import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_drive.oauth import credentials_from_dict
from app.connectors.google_drive.sync import _persist_refreshed_credentials
from app.crypto import decrypt_tokens
from app.models.connector import Connector
from app.services.ingestion import index_text_document
from app.services.meetings import upsert_meeting

logger = logging.getLogger(__name__)

GOOGLE_GMAIL = "google_gmail"
GOOGLE_CALENDAR = "google_calendar"


def _build_service(api_name: str, version: str, creds: Credentials):
    return build(api_name, version, credentials=creds)


def _decode_base64url(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode()).decode(errors="replace")


def _parse_message_body(payload: dict) -> str:
    data = payload.get("body", {}).get("data")
    if data:
        return _decode_base64url(data)
    return "\n".join(
        part_text
        for part in payload.get("parts", [])
        if (part_text := _parse_message_body(part)).strip()
    )


def _header(headers: list[dict], name: str) -> str:
    return next(
        (item.get("value", "") for item in headers if item.get("name", "").lower() == name.lower()),
        "",
    )


def _parse_rfc3339(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_event_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return _parse_rfc3339(value)


async def _credentials_for_connector(session: AsyncSession, connector: Connector) -> Credentials:
    creds = credentials_from_dict(decrypt_tokens(connector.oauth_tokens_encrypted))
    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, Request())
        await _persist_refreshed_credentials(session, connector, creds)
    return creds


async def _list_gmail_messages(service, max_messages: int) -> list[dict]:
    refs: list[dict] = []
    page_token = None
    while len(refs) < max_messages:
        response = await asyncio.to_thread(
            lambda token=page_token: service.users()
            .messages()
            .list(
                userId="me",
                maxResults=min(100, max_messages - len(refs)),
                pageToken=token,
                q="newer_than:180d",
            )
            .execute()
        )
        refs.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return refs[:max_messages]


async def run_gmail_sync(session: AsyncSession, connector: Connector, max_messages: int = 100) -> int:
    creds = await _credentials_for_connector(session, connector)
    service = await asyncio.to_thread(_build_service, "gmail", "v1", creds)
    message_refs = await _list_gmail_messages(service, max_messages)
    indexed = 0
    for message_ref in message_refs:
        message = await asyncio.to_thread(
            lambda ref=message_ref: service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        body = _parse_message_body(payload)
        subject = _header(headers, "Subject") or "Gmail message"
        sender = _header(headers, "From") or None
        internal_date = message.get("internalDate")
        updated_at = (
            datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
            if internal_date
            else datetime.now(timezone.utc)
        )
        text = f"Subject: {subject}\nFrom: {sender or 'Unknown'}\n\n{body}"
        await index_text_document(
            session,
            connector,
            external_id=message["id"],
            title=subject,
            text=text,
            mime_type="message/rfc822",
            updated_at=updated_at,
            source="Gmail",
            source_url=f"https://mail.google.com/mail/u/0/#all/{message['id']}",
            person=sender,
            extra_metadata={"thread_id": message.get("threadId")},
        )
        indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed


async def run_calendar_sync(session: AsyncSession, connector: Connector, max_events: int = 100) -> int:
    creds = await _credentials_for_connector(session, connector)
    service = await asyncio.to_thread(_build_service, "calendar", "v3", creds)
    now = datetime.now(timezone.utc)
    response = await asyncio.to_thread(
        lambda: service.events()
        .list(
            calendarId="primary",
            timeMin=(now - timedelta(days=90)).isoformat(),
            timeMax=(now + timedelta(days=180)).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_events,
        )
        .execute()
    )
    indexed = 0
    for event in response.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})
        start_value = start.get("dateTime") or start.get("date")
        end_value = end.get("dateTime") or end.get("date")
        starts_at = _parse_event_datetime(start_value)
        ends_at = _parse_event_datetime(end_value)
        attendees = [
            {
                "email": item.get("email"),
                "display_name": item.get("displayName"),
                "response_status": item.get("responseStatus"),
                "organizer": item.get("organizer", False),
            }
            for item in event.get("attendees", [])
        ]
        attendee_text = ", ".join(item.get("email", "") for item in attendees if item.get("email"))
        conference_entries = event.get("conferenceData", {}).get("entryPoints", [])
        join_url = next(
            (entry.get("uri") for entry in conference_entries if entry.get("entryPointType") == "video"),
            None,
        )
        title = event.get("summary", "Calendar event")
        text = (
            f"Event: {title}\n"
            f"Start: {start_value}\nEnd: {end_value}\n"
            f"Location: {event.get('location', '')}\n"
            f"Attendees: {attendee_text}\n\n{event.get('description', '')}"
        )
        await upsert_meeting(
            session,
            connector,
            provider=GOOGLE_CALENDAR,
            external_id=event["id"],
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            organizer=next((item.get("email") for item in attendees if item.get("organizer")), None),
            join_url=join_url,
            source_url=event.get("htmlLink"),
            attendees=attendees,
            metadata={"calendar_event_id": event["id"], "start_raw": start_value, "end_raw": end_value},
        )
        await index_text_document(
            session,
            connector,
            external_id=event["id"],
            title=title,
            text=text,
            mime_type="text/calendar",
            updated_at=_parse_rfc3339(event.get("updated")),
            source="Google Calendar",
            source_url=event.get("htmlLink"),
            person=attendee_text or None,
            extra_metadata={"start": start_value, "end": end_value, "join_url": join_url},
        )
        indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed
