import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import encrypt_tokens
from app.models.connector import Connector, ConnectorStatus

GOOGLE_DRIVE = "google_drive"
GOOGLE_GMAIL = "google_gmail"
GOOGLE_CALENDAR = "google_calendar"
GOOGLE_MEET = "google_meet"
GOOGLE_KEEP = "google_keep"


async def get_connector(session: AsyncSession, workspace_id: uuid.UUID, provider: str) -> Connector | None:
    return await session.scalar(
        select(Connector).where(Connector.workspace_id == workspace_id, Connector.provider == provider)
    )


async def get_or_create_pending_connector(session: AsyncSession, workspace_id: uuid.UUID, provider: str) -> Connector:
    connector = await get_connector(session, workspace_id, provider)
    if connector is None:
        connector = Connector(id=uuid.uuid4(), workspace_id=workspace_id, provider=provider, status=ConnectorStatus.PENDING)
        session.add(connector)
        await session.commit()
    return connector


async def save_oauth_tokens(session: AsyncSession, connector: Connector, tokens: dict) -> None:
    connector.oauth_tokens_encrypted = encrypt_tokens(tokens)
    connector.status = ConnectorStatus.CONNECTED
    await session.commit()
