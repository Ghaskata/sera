import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.connectors.google_drive.sync import run_incremental_sync
from app.connectors.google_workspace.sync import run_calendar_sync, run_gmail_sync
from app.database import async_session_factory
from app.models.connector import Connector, ConnectorStatus

logger = logging.getLogger(__name__)


async def _sync_all_connected_sources() -> None:
    async with async_session_factory() as session:
        connectors = (
            await session.scalars(select(Connector).where(Connector.status == ConnectorStatus.CONNECTED))
        ).all()

    for snapshot in connectors:
        async with async_session_factory() as session:
            connector = await session.get(Connector, snapshot.id)
            if connector is None:
                continue
            try:
                if connector.provider == "google_drive":
                    await run_incremental_sync(session, connector)
                elif connector.provider == "google_gmail":
                    await run_gmail_sync(session, connector)
                elif connector.provider == "google_calendar":
                    await run_calendar_sync(session, connector)
            except Exception:
                logger.exception("Incremental sync failed for connector %s", connector.id)


# Kept as a compatibility alias for callers using the original scheduler name.
_sync_all_connected_drives = _sync_all_connected_sources


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _sync_all_connected_sources,
        "interval",
        minutes=settings.drive_sync_interval_minutes,
        id="google_sources_sync",
    )
    return scheduler
