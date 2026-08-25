import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_drive.oauth import credentials_from_dict
from app.crypto import decrypt_tokens
from app.models.connector import Connector
from app.services.ingestion import index_text_document

logger = logging.getLogger(__name__)

GOOGLE_GMAIL = "google_gmail"
GOOGLE_CALENDAR = "google_calendar"


def _build_service(api_name: str, version: str, creds: Credentials):
    return build(api_name, version, credentials=creds)


def _parse_message_body(payload: dict) -> str:
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data.encode()).decode(errors="replace")
    return "\n".join(_parse_message_body(part) for part in payload.get("parts", []))


def _header(headers: list[dict], name: str) -> str:
    return next((item.get("value", "") for item in headers if item.get("name", "").lower() == name.lower()), "")


def _parse_rfc3339(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


async def run_gmail_sync(session: AsyncSession, connector: Connector, max_messages: int = 100) -> int:
    tokens = decrypt_tokens(connector.oauth_tokens_encrypted)
    creds = credentials_from_dict(tokens)
    service = await asyncio.to_thread(_build_service, "gmail", "v1", creds)
    response = await asyncio.to_thread(
        lambda: service.users().messages().list(userId="me", maxResults=max_messages, q="newer_than:180d").execute()
    )
    indexed = 0
    for message_ref in response.get("messages", []):
        message = await asyncio.to_thread(
            lambda ref=message_ref: service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
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
    tokens = decrypt_tokens(connector.oauth_tokens_encrypted)
    creds = credentials_from_dict(tokens)
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
        attendees = ", ".join(item.get("email", "") for item in event.get("attendees", []))
        text = (
            f"Event: {event.get('summary', 'Untitled event')}\n"
            f"Start: {start_value}\nEnd: {end_value}\n"
            f"Location: {event.get('location', '')}\n"
            f"Attendees: {attendees}\n\n{event.get('description', '')}"
        )
        await index_text_document(
            session,
            connector,
            external_id=event["id"],
            title=event.get("summary", "Calendar event"),
            text=text,
            mime_type="text/calendar",
            updated_at=_parse_rfc3339(event.get("updated")),
            source="Google Calendar",
            source_url=event.get("htmlLink"),
            person=attendees or None,
            extra_metadata={"start": start_value, "end": end_value},
        )
        indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed
