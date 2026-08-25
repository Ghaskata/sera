import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace


async def get_or_create_user_and_workspace(
    session: AsyncSession,
    telegram_user_id: int,
    name: str | None,
) -> tuple[User, Workspace]:
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if user is None:
        user = User(id=uuid.uuid4(), telegram_user_id=telegram_user_id, name=name)
        session.add(user)
        await session.flush()
    elif name and not user.name:
        user.name = name

    workspace = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if workspace is None:
        workspace = Workspace(id=uuid.uuid4(), owner_id=user.id, name=f"{user.name or 'My'} Workspace")
        session.add(workspace)
        await session.flush()

    await session.commit()
    return user, workspace


async def link_google_identity(
    session: AsyncSession,
    user: User,
    google_profile: dict,
) -> tuple[User, Workspace]:
    google_sub = google_profile.get("sub")
    email = google_profile.get("email")
    if not google_sub or not email:
        raise ValueError("Google did not return a stable account identity")

    existing = await session.scalar(select(User).where(User.google_sub == google_sub))
    if existing is not None and existing.id != user.id:
        raise ValueError("This Google account is already linked to another Sera user")

    existing_email = await session.scalar(select(User).where(User.email == email))
    if existing_email is not None and existing_email.id != user.id:
        raise ValueError("This Google email is already linked to another Sera user")

    user.google_sub = google_sub
    user.email = email
    user.name = google_profile.get("name") or user.name
    user.picture_url = google_profile.get("picture")
    user.last_login_at = datetime.now(timezone.utc)

    workspace = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if workspace is None:
        workspace = Workspace(id=uuid.uuid4(), owner_id=user.id, name=f"{user.name or 'My'} Workspace")
        session.add(workspace)

    await session.commit()
    return user, workspace
