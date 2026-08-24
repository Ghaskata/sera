import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.connectors.google_drive.sync import run_incremental_sync
from app.database import async_session_factory
from app.models.connector import Connector, ConnectorStatus

logger = logging.getLogger(__name__)


async def _sync_all_connected_drives() -> None:
    async with async_session_factory() as session:
        connectors = (
            await session.scalars(
                select(Connector).where(Connector.status == ConnectorStatus.CONNECTED, Connector.provider == "google_drive")
            )
        ).all()

    for connector in connectors:
        async with async_session_factory() as session:
            connector = await session.get(Connector, connector.id)
            try:
                await run_incremental_sync(session, connector)
            except Exception:
                logger.exception("Incremental sync failed for connector %s", connector.id)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _sync_all_connected_drives,
        "interval",
        minutes=settings.drive_sync_interval_minutes,
        id="drive_incremental_sync",
    )
    return scheduler
