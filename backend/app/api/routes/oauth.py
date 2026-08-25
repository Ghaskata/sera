import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.connectors.google_drive.oauth import exchange_code_for_tokens, fetch_google_profile
from app.database import async_session_factory
from app.models.user import User
from app.services.accounts import link_google_identity
from app.services.connectors import get_or_create_pending_connector, save_oauth_tokens
from app.services.oauth_state import consume_oauth_state
from app.telegram_bot.handlers import trigger_google_sync_and_notify

router = APIRouter()
logger = logging.getLogger(__name__)
SUPPORTED_GOOGLE_PROVIDERS = {"google_drive", "google_gmail", "google_calendar"}


@router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(code: str, state: str, error: str | None = None):
    if error:
        return HTMLResponse(
            f"<html><body>Google sign-in was cancelled or denied: {error}. You can close this window.</body></html>",
            status_code=400,
        )

    async with async_session_factory() as session:
        oauth_state = await consume_oauth_state(session, state)
        if oauth_state is None:
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        if oauth_state.provider not in SUPPORTED_GOOGLE_PROVIDERS:
            raise HTTPException(status_code=400, detail="Unsupported Google connector provider")

        try:
            tokens = await asyncio.to_thread(
                exchange_code_for_tokens,
                code=code,
                state=state,
                provider=oauth_state.provider,
            )
            profile = await fetch_google_profile(tokens["token"])
            user = await session.get(User, oauth_state.user_id)
            if user is None:
                raise ValueError("The Sera account that started sign-in no longer exists")
            user, workspace = await link_google_identity(session, user, profile)
            connector = await get_or_create_pending_connector(session, workspace.id, oauth_state.provider)
            await save_oauth_tokens(session, connector, tokens)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception:
            logger.exception("Google OAuth callback failed")
            raise HTTPException(status_code=502, detail="Google sign-in could not be completed") from None

        telegram_user_id = user.telegram_user_id
        connector_id = connector.id
        provider = oauth_state.provider

    if telegram_user_id is not None:
        asyncio.create_task(trigger_google_sync_and_notify(connector_id, telegram_user_id, provider))

    return (
        "<html><body>Google account connected. Sera is indexing your source. "
        "You can return to Telegram now.</body></html>"
    )
