import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, oauth
from app.scheduler import build_scheduler
from app.telegram_bot.bot import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = build_application()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    scheduler = build_scheduler()
    scheduler.start()

    logger.info("Sera backend started: Telegram bot polling + scheduler running")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


app = FastAPI(title="Sera Backend", lifespan=lifespan)
app.include_router(health.router)
app.include_router(oauth.router)
