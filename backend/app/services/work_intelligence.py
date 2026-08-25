import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_intelligence import Approval, AutomationCandidate, WorkEvent


DETECTED = "detected"
APPROVED = "approved"
REJECTED = "rejected"


def make_action_key(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return normalized[:120] or "unclassified-work"


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_workflow(event: WorkEvent) -> list[dict]:
    steps = event.event_metadata.get("steps") if event.event_metadata else None
    if steps:
        return [{"step": index + 1, "action": step} for index, step in enumerate(steps)]
    return [
        {"step": 1, "action": f"Detect {event.title}"},
        {"step": 2, "action": "Collect the required source data"},
        {"step": 3, "action": "Transform or summarize the result"},
        {"step": 4, "action": "Prepare the output for user approval"},
    ]


async def record_work_event(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    source: str,
    title: str,
    occurred_at: datetime,
    duration_minutes: int | None = None,
    metadata: dict | None = None,
) -> WorkEvent:
    event = WorkEvent(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        source=source,
        action_key=make_action_key(title),
        title=title,
        occurred_at=occurred_at,
        duration_minutes=duration_minutes,
        event_metadata=metadata or {},
    )
    session.add(event)
    await session.commit()
    return event


async def detect_automation_candidates(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    minimum_frequency: int = 3,
) -> list[AutomationCandidate]:
    events = list(
        (
            await session.scalars(
                select(WorkEvent)
                .where(WorkEvent.workspace_id == workspace_id)
                .order_by(WorkEvent.occurred_at.asc())
            )
        ).all()
    )
    grouped: dict[str, list[WorkEvent]] = defaultdict(list)
    for event in events:
        grouped[event.action_key].append(event)

    candidates: list[AutomationCandidate] = []
    for action_key, matching_events in grouped.items():
        if len(matching_events) < minimum_frequency:
            continue
        first = matching_events[0]
        first_seen = _as_utc(first.occurred_at)
        last_seen = _as_utc(matching_events[-1].occurred_at)
        total_minutes = sum(event.duration_minutes or 0 for event in matching_events)
        candidate = await session.scalar(
            select(AutomationCandidate).where(
                AutomationCandidate.workspace_id == workspace_id,
                AutomationCandidate.action_key == action_key,
            )
        )
        if candidate is None:
            candidate = AutomationCandidate(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                action_key=action_key,
                name=first.title,
                description=(
                    f"You have performed this task {len(matching_events)} times. "
                    "The sequence appears repetitive and may be automatable."
                ),
                frequency_count=len(matching_events),
                total_minutes=total_minutes,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
                status=DETECTED,
                workflow=build_workflow(first),
            )
            session.add(candidate)
        else:
            candidate.frequency_count = len(matching_events)
            candidate.total_minutes = total_minutes
            candidate.first_seen_at = first_seen
            candidate.last_seen_at = last_seen
            candidate.workflow = build_workflow(first)
        candidates.append(candidate)

    await session.commit()
    return candidates


def explain_candidate(candidate: AutomationCandidate) -> dict:
    average_minutes = (
        round(candidate.total_minutes / candidate.frequency_count, 1)
        if candidate.frequency_count
        else 0
    )
    return {
        "name": candidate.name,
        "frequency": candidate.frequency_count,
        "first_detected": _as_utc(candidate.first_seen_at).date().isoformat(),
        "last_performed": _as_utc(candidate.last_seen_at).date().isoformat(),
        "average_minutes": average_minutes,
        "total_minutes": candidate.total_minutes,
        "total_hours": round(candidate.total_minutes / 60, 1),
        "estimated_monthly_hours_saved": round(candidate.total_minutes / 60, 1),
        "message": (
            f"You have performed this task {candidate.frequency_count} times. "
            f"Average time: {average_minutes} minutes. This can likely be automated."
        ),
    }


async def create_approval(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    candidate: AutomationCandidate,
) -> Approval:
    approval = Approval(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        candidate_id=candidate.id,
        action_type="automation",
        payload={"workflow": candidate.workflow, "candidate_name": candidate.name},
        status="pending",
    )
    session.add(approval)
    await session.commit()
    return approval


async def review_approval(session: AsyncSession, approval_id: uuid.UUID, approved: bool) -> Approval:
    approval = await session.get(Approval, approval_id)
    if approval is None:
        raise ValueError("Approval not found")
    approval.status = APPROVED if approved else REJECTED
    approval.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    return approval
