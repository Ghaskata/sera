import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.connectors.google_drive.oauth import build_authorization_url
from app.connectors.google_drive.sync import run_full_sync
from app.database import async_session_factory
from app.models.connector import Connector, ConnectorStatus
from app.services.accounts import get_or_create_user_and_workspace
from app.services.connectors import GOOGLE_DRIVE, get_or_create_pending_connector
from app.search.rag import answer_question
from app.telegram_bot.registry import get_bot

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


async def _split_and_send(update: Update, text: str) -> None:
    for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
        await update.message.reply_text(text[i : i + TELEGRAM_MESSAGE_LIMIT])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)

    await update.message.reply_text(
        "Welcome to Sera. I can answer questions using your Google Drive files.\n\n"
        "Run /connect_drive to connect your Google Drive, then just ask me anything."
    )


async def connect_drive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        _, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        connector = await get_or_create_pending_connector(session, workspace.id, GOOGLE_DRIVE)

    # state carries the connector id so the OAuth callback knows which
    # connector + which Telegram user to notify once the flow completes.
    auth_url = build_authorization_url(state=str(connector.id))
    await update.message.reply_text(f"Connect your Google Drive:\n{auth_url}")


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    question = update.message.text

    async with async_session_factory() as session:
        _, workspace = await get_or_create_user_and_workspace(session, tg_user.id, tg_user.full_name)
        connector = await get_or_create_pending_connector(session, workspace.id, GOOGLE_DRIVE)
        if connector.status != ConnectorStatus.CONNECTED:
            await update.message.reply_text("Connect your Google Drive first with /connect_drive.")
            return

        result = await answer_question(session, workspace.id, question)

    text = result.answer
    if result.sources:
        text += "\n\nSources:\n" + "\n".join(
            f"- {s.title}" + (f" ({s.drive_link})" if s.drive_link else "") for s in result.sources
        )
    await _split_and_send(update, text)


async def trigger_sync_and_notify(connector_id, telegram_user_id: int) -> None:
    async with async_session_factory() as session:
        connector = await session.get(Connector, connector_id)
        if connector is None:
            return
        try:
            await run_full_sync(session, connector)
        except Exception:
            logger.exception("Initial Drive sync failed for connector %s", connector_id)

    bot = get_bot()
    if bot is not None:
        await bot.send_message(chat_id=telegram_user_id, text="Google Drive connected and indexed. Ask me anything!")
