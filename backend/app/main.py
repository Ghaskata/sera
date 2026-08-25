import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, connectors, health, oauth, rag
from app.config import settings
from app.scheduler import build_scheduler
from app.telegram_bot.bot import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = None
    scheduler = None
    if settings.start_telegram_in_web:
        bot_app = build_application()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
    if settings.start_scheduler_in_web:
        scheduler = build_scheduler()
        scheduler.start()

    logger.info(
        "Sera backend started: telegram_in_web=%s scheduler_in_web=%s",
        settings.start_telegram_in_web,
        settings.start_scheduler_in_web,
    )
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        if bot_app is not None:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()


app = FastAPI(title="Sera Backend", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(connectors.router)
app.include_router(oauth.router)
app.include_router(rag.router)
