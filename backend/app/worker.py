import asyncio
import logging

from app.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Sera background sync worker started")
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(run())
