import asyncio
import logging

from app.config import settings
from app.telegram_bot.bot import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    application = build_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Sera Telegram worker started")
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    asyncio.run(run())
