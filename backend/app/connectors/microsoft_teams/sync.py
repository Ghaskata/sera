import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt_tokens
from app.models.connector import Connector
from app.services.ingestion import index_text_document
from app.services.meetings import upsert_meeting

logger = logging.getLogger(__name__)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MICROSOFT_TEAMS = "microsoft_teams"


def _parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _graph_get(client: httpx.AsyncClient, token: str, path: str, params: dict | None = None) -> dict:
    response = await client.get(
        f"{GRAPH_BASE}/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
    )
    response.raise_for_status()
    return response.json()


async def _graph_pages(
    client: httpx.AsyncClient,
    token: str,
    path: str,
    params: dict | None = None,
    max_items: int = 100,
) -> list[dict]:
    items: list[dict] = []
    next_url = f"{GRAPH_BASE}/{path.lstrip('/')}"
    next_params = params or {}
    while next_url and len(items) < max_items:
        response = await client.get(
            next_url,
            headers={"Authorization": f"Bearer {token}"},
            params=next_params,
        )
        response.raise_for_status()
        payload = response.json()
        items.extend(payload.get("value", []))
        next_url = payload.get("@odata.nextLink")
        next_params = {}
    return items[:max_items]


async def _resolve_online_meeting_id(client: httpx.AsyncClient, token: str, join_url: str) -> str | None:
    try:
        meetings = await _graph_pages(
            client,
            token,
            "me/onlineMeetings",
            {"$filter": f"JoinWebUrl eq '{join_url.replace(chr(39), chr(39) * 2)}'"},
            max_items=1,
        )
    except httpx.HTTPStatusError:
        logger.info("Teams online meeting lookup unavailable for join URL")
        return None
    return meetings[0].get("id") if meetings else None


async def _fetch_transcript(client: httpx.AsyncClient, token: str, online_meeting_id: str) -> tuple[str | None, str | None]:
    try:
        transcripts = await _graph_pages(
            client,
            token,
            f"me/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts",
            {"$top": 20},
            max_items=20,
        )
        if not transcripts:
            return None, None
        transcript_id = transcripts[0].get("id")
        if not transcript_id:
            return None, None
        path = (
            f"me/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts/"
            f"{quote(transcript_id, safe='')}/content"
        )
        response = await client.get(
            f"{GRAPH_BASE}/{path}",
            headers={"Authorization": f"Bearer {token}"},
            params={"$format": "text/vtt"},
        )
        response.raise_for_status()
        return response.text, transcript_id
    except httpx.HTTPStatusError:
        logger.info("Teams transcript is not available or consent is incomplete")
        return None, None


async def run_teams_sync(
    session: AsyncSession,
    connector: Connector,
    max_events: int = 100,
) -> int:
    tokens = decrypt_tokens(connector.oauth_tokens_encrypted)
    token = tokens.get("access_token") or tokens.get("token")
    if not token:
        raise ValueError("Microsoft Teams connector has no access token")

    now = datetime.now(timezone.utc)
    params = {
        "startDateTime": (now - timedelta(days=90)).isoformat(),
        "endDateTime": (now + timedelta(days=180)).isoformat(),
        "$top": min(max_events, 100),
        "$orderby": "start/dateTime",
    }
    indexed = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        events = await _graph_pages(client, token, "me/calendarView", params, max_events)
        for event in events:
            event_id = event.get("id")
            if not event_id:
                continue
            online = event.get("onlineMeeting") or {}
            join_url = online.get("joinUrl") or online.get("joinWebUrl")
            attendees = [
                {
                    "email": item.get("emailAddress", {}).get("address"),
                    "display_name": item.get("emailAddress", {}).get("name"),
                    "response_status": item.get("status", {}).get("response"),
                    "organizer": item.get("type") == "organizer",
                }
                for item in event.get("attendees", [])
            ]
            start_value = (event.get("start") or {}).get("dateTime")
            end_value = (event.get("end") or {}).get("dateTime")
            title = event.get("subject") or "Microsoft Teams meeting"
            online_meeting_id = online.get("id")
            if not online_meeting_id and join_url:
                online_meeting_id = await _resolve_online_meeting_id(client, token, join_url)
            transcript_text = None
            transcript_id = None
            if online_meeting_id:
                transcript_text, transcript_id = await _fetch_transcript(client, token, online_meeting_id)
            attendee_text = ", ".join(
                item.get("email", "") for item in attendees if item.get("email")
            )
            body = (
                f"Meeting: {title}\n"
                f"Start: {start_value}\nEnd: {end_value}\n"
                f"Organizer: {(event.get('organizer') or {}).get('emailAddress', {}).get('address', '')}\n"
                f"Attendees: {attendee_text}\n"
                f"Join URL: {join_url or 'Not available'}\n\n"
                f"Body: {event.get('bodyPreview', '')}\n\n"
                f"Transcript:\n{transcript_text or 'Transcript not available yet.'}"
            )
            await upsert_meeting(
                session,
                connector,
                provider=MICROSOFT_TEAMS,
                external_id=event_id,
                title=title,
                starts_at=_parse_graph_datetime(start_value),
                ends_at=_parse_graph_datetime(end_value),
                organizer=(event.get("organizer") or {}).get("emailAddress", {}).get("address"),
                join_url=join_url,
                source_url=event.get("webLink"),
                attendees=attendees,
                transcript_status="available" if transcript_text else "not_available",
                transcript_external_id=transcript_id,
                notes=transcript_text,
                metadata={"online_meeting_id": online_meeting_id, "event_id": event_id},
            )
            await index_text_document(
                session,
                connector,
                external_id=event_id,
                title=title,
                text=body,
                mime_type="text/plain",
                updated_at=_parse_graph_datetime(event.get("lastModifiedDateTime")) or now,
                source="Microsoft Teams",
                source_url=event.get("webLink") or join_url,
                person=(event.get("organizer") or {}).get("emailAddress", {}).get("address"),
                extra_metadata={
                    "online_meeting_id": online_meeting_id,
                    "transcript_id": transcript_id,
                    "join_url": join_url,
                },
            )
            indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed
