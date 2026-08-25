import asyncio
import logging
from html import escape

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from fastapi.responses import HTMLResponse

from app.connectors.google_drive.oauth import exchange_code_for_tokens, fetch_google_profile
from app.connectors.microsoft_teams.oauth import exchange_microsoft_code, microsoft_profile
from app.connectors.slack.oauth import exchange_slack_code, slack_auth_test
from app.database import async_session_factory
from app.models.user import User
from app.services.accounts import link_google_identity
from app.services.connectors import get_or_create_pending_connector, save_oauth_tokens
from app.services.oauth_state import consume_oauth_state
from app.telegram_bot.handlers import trigger_connector_sync_and_notify

router = APIRouter()
logger = logging.getLogger(__name__)
SUPPORTED_GOOGLE_PROVIDERS = {"google_drive", "google_gmail", "google_calendar", "google_meet"}
SUPPORTED_PROVIDERS = SUPPORTED_GOOGLE_PROVIDERS | {"slack", "microsoft_teams"}


async def _get_user(session, user_id):
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("The Sera account that started sign-in no longer exists")
    return user


@router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(code: str, state: str, error: str | None = None):
    return await _oauth_callback("google", code, state, error)


@router.get("/oauth/slack/callback", response_class=HTMLResponse)
async def slack_oauth_callback(code: str, state: str, error: str | None = None):
    return await _oauth_callback("slack", code, state, error)


@router.get("/oauth/microsoft/callback", response_class=HTMLResponse)
async def microsoft_oauth_callback(code: str, state: str, error: str | None = None):
    return await _oauth_callback("microsoft", code, state, error)


async def _oauth_callback(provider_family: str, code: str, state: str, error: str | None):
    if error:
        return HTMLResponse(
            f"<html><body>{escape(provider_family.title())} sign-in was cancelled or denied: {escape(error)}. "
            "You can close this window.</body></html>",
            status_code=400,
        )

    async with async_session_factory() as session:
        oauth_state = await consume_oauth_state(session, state)
        if oauth_state is None:
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        if oauth_state.provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        if (
            provider_family == "google" and oauth_state.provider not in SUPPORTED_GOOGLE_PROVIDERS
        ) or (provider_family != "google" and oauth_state.provider != provider_family):
            raise HTTPException(status_code=400, detail="OAuth provider does not match callback")

        try:
            user = await _get_user(session, oauth_state.user_id)
            if provider_family == "google":
                tokens = await asyncio.to_thread(
                    exchange_code_for_tokens,
                    code=code,
                    state=state,
                    provider=oauth_state.provider,
                )
                profile = await fetch_google_profile(tokens["token"])
                user, workspace = await link_google_identity(session, user, profile)
            elif provider_family == "slack":
                tokens = await exchange_slack_code(code, state)
                auth = await slack_auth_test(tokens["access_token"])
                workspace = await _workspace_for_user(session, user)
                tokens = {**tokens, "auth_test": auth}
            else:
                tokens = await exchange_microsoft_code(code, state)
                profile = await microsoft_profile(tokens["access_token"])
                workspace = await _workspace_for_user(session, user)
                tokens = {**tokens, "microsoft_profile": profile}

            connector = await get_or_create_pending_connector(session, workspace.id, oauth_state.provider)
            await save_oauth_tokens(session, connector, tokens)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception:
            logger.exception("%s OAuth callback failed", provider_family)
            raise HTTPException(status_code=502, detail="OAuth connection could not be completed") from None

        telegram_user_id = user.telegram_user_id
        connector_id = connector.id
        connector_provider = oauth_state.provider

    if telegram_user_id is not None:
        asyncio.create_task(
            trigger_connector_sync_and_notify(connector_id, telegram_user_id, connector_provider)
        )

    return (
        f"<html><body>{provider_family.title()} account connected. "
        "Sera is syncing the permitted data. You can return to Telegram now.</body></html>"
    )


async def _workspace_for_user(session, user: User):
    from app.models.workspace import Workspace

    workspace = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if workspace is None:
        raise ValueError("The Sera workspace for this account could not be found")
    return workspace
