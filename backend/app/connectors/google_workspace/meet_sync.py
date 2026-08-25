import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_workspace.sync import _credentials_for_connector
from app.models.connector import Connector
from app.services.ingestion import index_text_document
from app.services.meetings import upsert_meeting

logger = logging.getLogger(__name__)
MEET_API_BASE = "https://meet.googleapis.com/v2"
GOOGLE_MEET = "google_meet"


async def _get_json(client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict:
    response = await client.get(f"{MEET_API_BASE}/{path.lstrip('/')}", params=params)
    response.raise_for_status()
    return response.json()


async def _list_transcript_entries(client: httpx.AsyncClient, transcript_name: str) -> list[dict]:
    entries: list[dict] = []
    page_token = None
    while True:
        response = await _get_json(
            client,
            f"{transcript_name}/entries",
            {"pageSize": 100, "pageToken": page_token} if page_token else {"pageSize": 100},
        )
        entries.extend(response.get("transcriptEntries", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return entries


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _transcript_text(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        participant = entry.get("participant", "Participant")
        text = entry.get("text", "").strip()
        if text:
            lines.append(f"{participant}: {text}")
    return "\n".join(lines)


async def run_google_meet_sync(
    session: AsyncSession,
    connector: Connector,
    max_records: int = 100,
) -> int:
    creds = await _credentials_for_connector(session, connector)
    headers: dict[str, str] = {}
    creds.apply(headers)
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await _get_json(client, "conferenceRecords", {"pageSize": min(max_records, 100)})
        records = response.get("conferenceRecords", [])[:max_records]
        indexed = 0
        for record in records:
            record_name = record.get("name")
            if not record_name:
                continue
            space = record.get("space", {})
            meeting_code = space.get("meetingCode")
            title = f"Google Meet — {meeting_code or record_name.rsplit('/', 1)[-1]}"
            transcript_response = await _get_json(client, f"{record_name}/transcripts", {"pageSize": 20})
            transcripts = transcript_response.get("transcripts", [])
            transcript = transcripts[0] if transcripts else None
            transcript_name = transcript.get("name") if transcript else None
            entries = await _list_transcript_entries(client, transcript_name) if transcript_name else []
            transcript_text = _transcript_text(entries)
            join_url = f"https://meet.google.com/{meeting_code}" if meeting_code else None
            starts_at = _parse_time(record.get("startTime"))
            ends_at = _parse_time(record.get("endTime"))
            transcript_status = "available" if transcript_text else ("empty" if transcript else "not_available")
            await upsert_meeting(
                session,
                connector,
                provider=GOOGLE_MEET,
                external_id=record_name,
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
                join_url=join_url,
                source_url=join_url,
                transcript_status=transcript_status,
                transcript_external_id=transcript_name,
                notes=transcript_text or None,
                metadata={"conference_record": record},
            )
            meeting_text = (
                f"Meeting: {title}\n"
                f"Start: {record.get('startTime')}\nEnd: {record.get('endTime')}\n"
                f"Meeting code: {meeting_code or 'unknown'}\n\n"
                f"Transcript:\n{transcript_text or 'Transcript not available yet.'}"
            )
            await index_text_document(
                session,
                connector,
                external_id=record_name,
                title=title,
                text=meeting_text,
                mime_type="text/plain",
                updated_at=ends_at or starts_at or datetime.now(timezone.utc),
                source="Google Meet",
                source_url=join_url,
                extra_metadata={
                    "conference_record": record_name,
                    "transcript": transcript_name,
                    "meeting_code": meeting_code,
                },
            )
            indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed
