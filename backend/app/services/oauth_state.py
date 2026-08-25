import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_state import OAuthState

STATE_TTL_MINUTES = 10


async def create_oauth_state(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    provider: str = "google",
    purpose: str = "login_and_drive",
) -> OAuthState:
    oauth_state = OAuthState(
        id=uuid.uuid4(),
        state=secrets.token_urlsafe(32),
        user_id=user_id,
        provider=provider,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=STATE_TTL_MINUTES),
    )
    session.add(oauth_state)
    await session.commit()
    return oauth_state


async def consume_oauth_state(session: AsyncSession, value: str) -> OAuthState | None:
    oauth_state = await session.scalar(select(OAuthState).where(OAuthState.state == value))
    if oauth_state is None or oauth_state.used_at is not None:
        return None

    now = datetime.now(timezone.utc)
    expires_at = oauth_state.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        return None

    oauth_state.used_at = now
    await session.commit()
    return oauth_state
