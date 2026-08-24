import asyncio
import logging
import uuid
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_drive.extract import SUPPORTED_MIME_TYPES, extract_text
from app.connectors.google_drive.oauth import credentials_from_dict, credentials_to_dict
from app.crypto import decrypt_tokens, encrypt_tokens
from app.models.chunk import Chunk
from app.models.connector import Connector
from app.models.document import Document
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

logger = logging.getLogger(__name__)

DRIVE_LIST_FIELDS = "nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)"


def _build_drive_service(creds: Credentials):
    return build("drive", "v3", credentials=creds)


async def _get_credentials(connector: Connector) -> Credentials:
    tokens = decrypt_tokens(connector.oauth_tokens_encrypted)
    return credentials_from_dict(tokens)


async def _persist_refreshed_credentials(session: AsyncSession, connector: Connector, creds: Credentials) -> None:
    if creds.token != decrypt_tokens(connector.oauth_tokens_encrypted).get("token"):
        connector.oauth_tokens_encrypted = encrypt_tokens(credentials_to_dict(creds))
        await session.commit()


async def _process_file(session: AsyncSession, connector: Connector, drive_service, file: dict) -> None:
    mime_type = file["mimeType"]
    if mime_type not in SUPPORTED_MIME_TYPES:
        logger.info("Skipping unsupported file type %s (%s)", file["name"], mime_type)
        return

    try:
        text = await asyncio.to_thread(extract_text, drive_service, file["id"], mime_type)
    except Exception:
        logger.exception("Failed to extract text for file %s", file["id"])
        return

    if not text or not text.strip():
        logger.info("No extractable text for file %s, skipping", file["name"])
        return

    existing = await session.scalar(
        select(Document).where(Document.connector_id == connector.id, Document.external_id == file["id"])
    )
    updated_at = datetime.fromisoformat(file["modifiedTime"].replace("Z", "+00:00"))

    if existing:
        # Re-index: drop old chunks, keep the document row.
        await session.execute(
            Chunk.__table__.delete().where(Chunk.document_id == existing.id)
        )
        existing.title = file["name"]
        existing.mime_type = mime_type
        existing.drive_link = file.get("webViewLink")
        existing.updated_at = updated_at
        document = existing
    else:
        document = Document(
            id=uuid.uuid4(),
            workspace_id=connector.workspace_id,
            connector_id=connector.id,
            external_id=file["id"],
            title=file["name"],
            mime_type=mime_type,
            drive_link=file.get("webViewLink"),
            updated_at=updated_at,
        )
        session.add(document)
    await session.flush()

    pieces = chunk_text(text)
    if not pieces:
        await session.commit()
        return

    vectors = await embed_texts(pieces)
    for piece, vector in zip(pieces, vectors):
        session.add(
            Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                workspace_id=connector.workspace_id,
                text=piece,
                embedding=vector,
                chunk_metadata={"drive_link": file.get("webViewLink"), "title": file["name"]},
            )
        )
    await session.commit()


async def run_full_sync(session: AsyncSession, connector: Connector) -> None:
    creds = await _get_credentials(connector)
    drive_service = await asyncio.to_thread(_build_drive_service, creds)
    await _persist_refreshed_credentials(session, connector, creds)

    page_token = None
    while True:
        response = await asyncio.to_thread(
            lambda: drive_service.files()
            .list(pageSize=100, fields=DRIVE_LIST_FIELDS, pageToken=page_token)
            .execute()
        )
        for file in response.get("files", []):
            await _process_file(session, connector, drive_service, file)
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    start_token = await asyncio.to_thread(lambda: drive_service.changes().getStartPageToken().execute())
    connector.drive_start_page_token = start_token["startPageToken"]
    connector.status = "connected"
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()


async def run_incremental_sync(session: AsyncSession, connector: Connector) -> None:
    if not connector.drive_start_page_token:
        await run_full_sync(session, connector)
        return

    creds = await _get_credentials(connector)
    drive_service = await asyncio.to_thread(_build_drive_service, creds)
    await _persist_refreshed_credentials(session, connector, creds)

    page_token = connector.drive_start_page_token
    while page_token:
        response = await asyncio.to_thread(
            lambda: drive_service.changes()
            .list(pageToken=page_token, fields="nextPageToken, newStartPageToken, changes(fileId, removed, file(id, name, mimeType, modifiedTime, webViewLink))")
            .execute()
        )
        for change in response.get("changes", []):
            if change.get("removed"):
                continue
            file = change.get("file")
            if file:
                await _process_file(session, connector, drive_service, file)

        if "newStartPageToken" in response:
            connector.drive_start_page_token = response["newStartPageToken"]
            page_token = None
        else:
            page_token = response.get("nextPageToken")

    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
