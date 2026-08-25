from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.config import settings
from app.telegram_bot import handlers
from app.telegram_bot.registry import set_bot


def build_application() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("login", handlers.login_google))
    application.add_handler(CommandHandler("connect_google", handlers.login_google))
    application.add_handler(CommandHandler("connect", handlers.connect_menu))
    application.add_handler(CommandHandler("connect_gmail", handlers.connect_gmail))
    application.add_handler(CommandHandler("connect_calendar", handlers.connect_calendar))
    application.add_handler(CommandHandler("connect_meet", handlers.connect_meet))
    application.add_handler(CommandHandler("connect_notes", handlers.connect_notes))
    application.add_handler(CommandHandler("connect_slack", handlers.connect_slack))
    application.add_handler(CommandHandler("connect_teams", handlers.connect_teams))
    application.add_handler(CommandHandler("connections", handlers.connections_status))
    application.add_handler(CommandHandler("status", handlers.connections_status))
    application.add_handler(CommandHandler("connect_drive", handlers.connect_drive))
    application.add_handler(CommandHandler("insights", handlers.insights))
    application.add_handler(CommandHandler("why", handlers.why))
    application.add_handler(CallbackQueryHandler(handlers.connector_button, pattern=r"^setup:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.ask))

    set_bot(application.bot)
    return application
