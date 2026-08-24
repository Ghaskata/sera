import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.connectors.google_drive.oauth import exchange_code_for_tokens
from app.database import async_session_factory
from app.models.connector import Connector
from app.models.user import User
from app.models.workspace import Workspace
from app.services.connectors import save_oauth_tokens
from app.telegram_bot.handlers import trigger_sync_and_notify

router = APIRouter()


@router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(code: str, state: str):
    connector_id = uuid.UUID(state)

    async with async_session_factory() as session:
        connector = await session.get(Connector, connector_id)
        if connector is None:
            raise HTTPException(status_code=404, detail="Unknown connector")

        tokens = exchange_code_for_tokens(code=code, state=state)
        await save_oauth_tokens(session, connector, tokens)

        workspace = await session.get(Workspace, connector.workspace_id)
        user = await session.get(User, workspace.owner_id)
        telegram_user_id = user.telegram_user_id

    # Sync happens after we've returned an HTTP response to the browser.
    asyncio.create_task(trigger_sync_and_notify(connector_id, telegram_user_id))

    return "<html><body>Google Drive connected. You can return to Telegram now.</body></html>"
