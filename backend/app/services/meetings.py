import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector
from app.models.meeting import Meeting


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def upsert_meeting(
    session: AsyncSession,
    connector: Connector,
    *,
    provider: str,
    external_id: str,
    title: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    organizer: str | None = None,
    join_url: str | None = None,
    source_url: str | None = None,
    attendees: list[dict] | None = None,
    transcript_status: str = "not_requested",
    transcript_external_id: str | None = None,
    notes: str | None = None,
    metadata: dict | None = None,
) -> Meeting:
    meeting = await session.scalar(
        select(Meeting).where(
            Meeting.connector_id == connector.id,
            Meeting.external_id == external_id,
        )
    )
    if meeting is None:
        meeting = Meeting(
            id=uuid.uuid4(),
            workspace_id=connector.workspace_id,
            connector_id=connector.id,
            provider=provider,
            external_id=external_id,
            title=title,
            starts_at=_utc(starts_at),
            ends_at=_utc(ends_at),
            organizer=organizer,
            join_url=join_url,
            source_url=source_url,
            attendees=attendees or [],
            transcript_status=transcript_status,
            transcript_external_id=transcript_external_id,
            notes=notes,
            meeting_metadata=metadata or {},
            updated_at=datetime.now(timezone.utc),
        )
        session.add(meeting)
    else:
        meeting.provider = provider
        meeting.title = title
        meeting.starts_at = _utc(starts_at)
        meeting.ends_at = _utc(ends_at)
        meeting.organizer = organizer
        meeting.join_url = join_url
        meeting.source_url = source_url
        meeting.attendees = attendees or []
        meeting.transcript_status = transcript_status
        meeting.transcript_external_id = transcript_external_id
        meeting.notes = notes
        meeting.meeting_metadata = metadata or {}
        meeting.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return meeting
