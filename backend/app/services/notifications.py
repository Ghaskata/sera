import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a Telegram message directly for web/worker processes without a bot registry."""
    if not settings.telegram_bot_token:
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN is not configured")
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json={"chat_id": chat_id, "text": text})
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Telegram notification failed for chat %s", chat_id)
        return False
