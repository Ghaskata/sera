"""Holds the running bot instance so other parts of the app (e.g. the OAuth
callback route) can send messages to users without importing the whole
telegram Application wiring."""

from telegram import Bot

_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


def get_bot() -> Bot | None:
    return _bot
