import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.connector import Connector
from app.models.document import Document
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


async def index_text_document(
    session: AsyncSession,
    connector: Connector,
    *,
    external_id: str,
    title: str,
    text: str,
    mime_type: str,
    updated_at: datetime | None = None,
    source: str,
    source_url: str | None = None,
    person: str | None = None,
    extra_metadata: dict | None = None,
) -> Document | None:
    if not text or not text.strip():
        return None

    vector_store = get_vector_store()
    existing = await session.scalar(
        select(Document).where(
            Document.connector_id == connector.id,
            Document.external_id == external_id,
        )
    )
    normalized_updated_at = updated_at or datetime.now(timezone.utc)
    if normalized_updated_at.tzinfo is None:
        normalized_updated_at = normalized_updated_at.replace(tzinfo=timezone.utc)

    if existing is None:
        document = Document(
            id=uuid.uuid4(),
            workspace_id=connector.workspace_id,
            connector_id=connector.id,
            external_id=external_id,
            title=title,
            mime_type=mime_type,
            drive_link=source_url,
            updated_at=normalized_updated_at,
        )
        session.add(document)
    else:
        document = existing
        if vector_store:
            try:
                await vector_store.delete_document(str(document.id), str(connector.workspace_id))
            except Exception:
                logger.exception("Could not remove old external vectors for document %s", document.id)
        await session.execute(Chunk.__table__.delete().where(Chunk.document_id == document.id))
        document.title = title
        document.mime_type = mime_type
        document.drive_link = source_url
        document.updated_at = normalized_updated_at
    await session.flush()

    pieces = chunk_text(text)
    vectors = await embed_texts(pieces) if pieces else []
    base_metadata = {
        "title": title,
        "source": source,
        "date": normalized_updated_at.date().isoformat(),
        "person": person,
        "url": source_url,
        "drive_link": source_url,
    }
    if extra_metadata:
        base_metadata.update(extra_metadata)

    vector_records = []
    for piece, vector in zip(pieces, vectors):
        chunk = Chunk(
            id=uuid.uuid4(),
            document_id=document.id,
            workspace_id=connector.workspace_id,
            text=piece,
            embedding=vector,
            chunk_metadata=base_metadata,
        )
        session.add(chunk)
        vector_records.append(
            {
                "id": str(chunk.id),
                "document_id": str(document.id),
                "workspace_id": str(connector.workspace_id),
                "text": piece,
                "embedding": vector,
                **base_metadata,
            }
        )
    await session.commit()

    if vector_store and vector_records:
        try:
            await vector_store.upsert_chunks(vector_records)
        except Exception:
            logger.exception("External vector upsert failed for document %s", document.id)
    return document
