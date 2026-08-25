import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_drive.oauth import credentials_from_dict
from app.connectors.google_drive.sync import _persist_refreshed_credentials
from app.crypto import decrypt_tokens
from app.config import settings
from app.models.connector import Connector
from app.services.ingestion import index_text_document

logger = logging.getLogger(__name__)
KEEP_BASE_URL = "https://keep.googleapis.com/v1"
GOOGLE_KEEP = "google_keep"


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _note_text(note: dict[str, Any]) -> str:
    body = note.get("body") or {}
    text = body.get("text") or body.get("textContent") or ""
    labels = ", ".join(label.get("name", "") for label in note.get("labels", []))
    return f"Title: {note.get('title', 'Untitled note')}\nLabels: {labels}\n\n{text}".strip()


async def _keep_credentials(session: AsyncSession, connector: Connector) -> Credentials:
    creds = credentials_from_dict(decrypt_tokens(connector.oauth_tokens_encrypted))
    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, Request())
        await _persist_refreshed_credentials(session, connector, creds)
    return creds


async def _list_notes(client: httpx.AsyncClient, max_notes: int) -> list[dict]:
    notes: list[dict] = []
    page_token = None
    while len(notes) < max_notes:
        params = {"pageSize": min(100, max_notes - len(notes))}
        if page_token:
            params["pageToken"] = page_token
        response = await client.get(f"{KEEP_BASE_URL}/notes", params=params)
        response.raise_for_status()
        payload = response.json()
        notes.extend(payload.get("notes", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return notes[:max_notes]


async def run_keep_sync(
    session: AsyncSession,
    connector: Connector,
    max_notes: int | None = None,
) -> int:
    creds = await _keep_credentials(session, connector)
    headers: dict[str, str] = {}
    creds.apply(headers)
    limit = max_notes or settings.notes_sync_max_records
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        notes = await _list_notes(client, limit)
        for note in notes:
            note_name = note.get("name")
            if not note_name:
                continue
            title = note.get("title") or "Google Keep note"
            await index_text_document(
                session,
                connector,
                external_id=note_name,
                title=title,
                text=_note_text(note),
                mime_type="text/plain",
                updated_at=_parse_time(note.get("updateTime")),
                source="Google Keep",
                source_url=f"https://keep.google.com/",
                extra_metadata={"note_name": note_name, "create_time": note.get("createTime")},
            )
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return len(notes)
