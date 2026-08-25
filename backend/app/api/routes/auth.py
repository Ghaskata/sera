import asyncio
import logging

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.connectors.catalog import CONNECTOR_CATALOG
from app.connectors.google_drive.oauth import build_authorization_url, exchange_code_for_tokens, fetch_google_profile
from app.connectors.microsoft_teams.oauth import build_microsoft_authorization_url
from app.connectors.slack.oauth import build_slack_authorization_url
from app.database import async_session_factory
from app.models.connector import Connector
from app.models.user import User
from app.services.accounts import link_google_identity
from app.services.connectors import get_or_create_pending_connector, save_oauth_tokens
from app.services.oauth_state import consume_oauth_state, create_oauth_state
from app.services.web_auth import WEB_SESSION_COOKIE, create_web_session, get_web_auth_context, revoke_web_session
from app.search.rag import query_connected_sources
from app.api.routes.rag import RagQueryResponse, RagSourceResponse
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
GOOGLE_WEB_PROVIDER = "google_drive"


class SessionRagQueryRequest(BaseModel):
    question: str
    source_types: set[str] | None = None


SUPPORTED_WEB_CONNECTORS = {
    "google_drive",
    "google_gmail",
    "google_calendar",
    "google_meet",
    "google_keep",
    "slack",
    "microsoft_teams",
}


def _set_session_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        WEB_SESSION_COOKIE,
        token,
        max_age=settings.web_session_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.web_cookie_secure,
        samesite="lax",
        path="/",
    )


async def _require_context(cookie: str | None):
    async with async_session_factory() as session:
        context = await get_web_auth_context(session, cookie)
    if context is None:
        raise HTTPException(status_code=401, detail="Sign in with Google to continue")
    return context


@router.get("/google/start")
async def start_google_web_login():
    async with async_session_factory() as session:
        state = await create_oauth_state(
            session,
            user_id=None,
            provider=GOOGLE_WEB_PROVIDER,
            purpose="web_login",
        )
    url = build_authorization_url(
        state=state.state,
        provider=GOOGLE_WEB_PROVIDER,
        redirect_uri=settings.google_web_oauth_redirect_uri,
    )
    return RedirectResponse(url=url, status_code=307)


@router.get("/google/callback")
async def complete_google_web_login(code: str, state: str, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Google sign-in was cancelled: {error}")

    async with async_session_factory() as session:
        oauth_state = await consume_oauth_state(session, state)
        if oauth_state is None or oauth_state.provider != GOOGLE_WEB_PROVIDER or oauth_state.purpose != "web_login":
            raise HTTPException(status_code=400, detail="Invalid or expired web login state")
        try:
            tokens = await asyncio.to_thread(
                exchange_code_for_tokens,
                code=code,
                state=state,
                provider=GOOGLE_WEB_PROVIDER,
                redirect_uri=settings.google_web_oauth_redirect_uri,
            )
            profile = await fetch_google_profile(tokens["token"])
            if profile.get("email_verified") is False:
                raise ValueError("Google email is not verified")
            google_sub = profile.get("sub")
            email = profile.get("email")
            user = await session.scalar(select(User).where(User.google_sub == google_sub))
            if user is None and email:
                user = await session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(name=profile.get("name"), email=email, google_sub=google_sub)
                session.add(user)
                await session.flush()
            user, workspace = await link_google_identity(session, user, profile)
            connector = await get_or_create_pending_connector(session, workspace.id, GOOGLE_WEB_PROVIDER)
            await save_oauth_tokens(session, connector, tokens)
            session_token = await create_web_session(session, user, workspace)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception:
            logger.exception("Web Google OAuth callback failed")
            raise HTTPException(status_code=502, detail="Google sign-in could not be completed") from None

    response = RedirectResponse(url=f"{settings.web_frontend_origin}/?auth=success", status_code=303)
    _set_session_cookie(response, session_token)
    return response


@router.get("/me")
async def current_user(sera_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)):
    context = await _require_context(sera_session)
    return {
        "user_id": str(context.user_id),
        "workspace_id": str(context.workspace_id),
        "email": context.email,
        "name": context.name,
    }


@router.post("/logout")
async def logout(sera_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)):
    async with async_session_factory() as session:
        await revoke_web_session(session, sera_session)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(WEB_SESSION_COOKIE, path="/")
    return response


@router.get("/connectors")
async def current_connectors(sera_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)):
    context = await _require_context(sera_session)
    async with async_session_factory() as session:
        connected = {
            connector.provider: connector
            for connector in (
                await session.scalars(select(Connector).where(Connector.workspace_id == context.workspace_id))
            ).all()
        }
    rows = []
    for definition in CONNECTOR_CATALOG:
        connector = connected.get(definition.provider)
        rows.append(
            {
                "provider": definition.provider,
                "display_name": definition.display_name,
                "capabilities": list(definition.capabilities),
                "status": connector.status if connector else definition.status,
                "last_sync_at": connector.last_sync_at.isoformat() if connector and connector.last_sync_at else None,
                "setup_mode": definition.setup_mode,
                "note": definition.note,
            }
        )
    return {"workspace_id": str(context.workspace_id), "connectors": rows}


@router.get("/connectors/{provider}/start")
async def start_connector_setup(
    provider: str,
    sera_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE),
):
    context = await _require_context(sera_session)
    if provider not in SUPPORTED_WEB_CONNECTORS:
        raise HTTPException(status_code=400, detail="This connector is not available for web OAuth setup")
    async with async_session_factory() as session:
        state = await create_oauth_state(session, context.user_id, provider=provider, purpose="web_connector_link")
    if provider.startswith("google_"):
        url = build_authorization_url(state=state.state, provider=provider)
    elif provider == "slack":
        url = build_slack_authorization_url(state.state)
    else:
        url = build_microsoft_authorization_url(state.state)
    return RedirectResponse(url=url, status_code=307)


@router.post("/rag/query", response_model=RagQueryResponse)
async def query_from_session(
    payload: SessionRagQueryRequest,
    sera_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE),
) -> RagQueryResponse:
    context = await _require_context(sera_session)
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="question must be a non-empty string")

    async with async_session_factory() as session:
        result = await query_connected_sources(
            session,
            context.workspace_id,
            payload.question,
            source_types=payload.source_types,
        )
    return RagQueryResponse(
        answer=result.answer,
        sources=[
            RagSourceResponse(
                title=source.title,
                source=source.source,
                date=source.date,
                person=source.person,
                url=source.url,
                drive_link=source.drive_link,
            )
            for source in result.sources
        ],
    )
