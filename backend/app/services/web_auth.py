import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.web_session import WebSession
from app.models.workspace import Workspace

WEB_SESSION_COOKIE = "sera_session"


@dataclass(frozen=True)
class WebAuthContext:
    session_id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    email: str | None
    name: str | None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.web_session_ttl_days)


async def create_web_session(
    session: AsyncSession,
    user: User,
    workspace: Workspace,
) -> str:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    session.add(
        WebSession(
            id=uuid.uuid4(),
            session_hash=_hash_token(raw_token),
            user_id=user.id,
            workspace_id=workspace.id,
            expires_at=_expiry(),
            last_seen_at=now,
        )
    )
    await session.commit()
    return raw_token


async def get_web_auth_context(
    session: AsyncSession,
    raw_token: str | None,
) -> WebAuthContext | None:
    if not raw_token:
        return None
    web_session = await session.scalar(
        select(WebSession).where(WebSession.session_hash == _hash_token(raw_token))
    )
    if web_session is None:
        return None
    now = datetime.now(timezone.utc)
    expires_at = web_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if web_session.revoked_at is not None or expires_at <= now:
        return None

    user = await session.get(User, web_session.user_id)
    workspace = await session.get(Workspace, web_session.workspace_id)
    if user is None or workspace is None or workspace.owner_id != user.id:
        return None

    web_session.last_seen_at = now
    await session.commit()
    return WebAuthContext(
        session_id=web_session.id,
        user_id=user.id,
        workspace_id=workspace.id,
        email=user.email,
        name=user.name,
    )


async def revoke_web_session(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    web_session = await session.scalar(
        select(WebSession).where(WebSession.session_hash == _hash_token(raw_token))
    )
    if web_session is not None:
        web_session.revoked_at = datetime.now(timezone.utc)
        await session.commit()
