import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace


async def get_or_create_user_and_workspace(session: AsyncSession, telegram_user_id: int, name: str | None) -> tuple[User, Workspace]:
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if user is None:
        user = User(id=uuid.uuid4(), telegram_user_id=telegram_user_id, name=name)
        session.add(user)
        await session.flush()

    workspace = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if workspace is None:
        workspace = Workspace(id=uuid.uuid4(), owner_id=user.id, name=f"{name or 'My'} Workspace")
        session.add(workspace)
        await session.flush()

    await session.commit()
    return user, workspace
