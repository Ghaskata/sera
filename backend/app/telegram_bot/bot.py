from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.config import settings
from app.telegram_bot import handlers
from app.telegram_bot.registry import set_bot


def build_application() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("connect_drive", handlers.connect_drive))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.ask))

    set_bot(application.bot)
    return application
