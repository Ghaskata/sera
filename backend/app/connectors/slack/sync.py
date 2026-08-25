import asyncio
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt_tokens
from app.models.connector import Connector
from app.services.ingestion import index_text_document

SLACK_API_BASE = "https://slack.com/api"


async def _slack_call(
    client: httpx.AsyncClient,
    method: str,
    token: str,
    params: dict | None = None,
) -> dict:
    response = await client.get(
        f"{SLACK_API_BASE}/{method}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise ValueError(payload.get("error", f"Slack API call failed: {method}"))
    return payload


async def _list_all(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    key: str,
    params: dict,
    max_items: int,
) -> list[dict]:
    items: list[dict] = []
    cursor = None
    while len(items) < max_items:
        request_params = {**params, "limit": min(200, max_items - len(items))}
        if cursor:
            request_params["cursor"] = cursor
        payload = await _slack_call(client, method, token, request_params)
        items.extend(payload.get(key, []))
        cursor = payload.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return items[:max_items]


async def run_slack_sync(
    session: AsyncSession,
    connector: Connector,
    max_channels: int = 50,
    max_messages_per_channel: int = 100,
) -> int:
    tokens = decrypt_tokens(connector.oauth_tokens_encrypted)
    token = tokens.get("access_token") or tokens.get("token")
    if not token:
        raise ValueError("Slack connector has no access token")
    team_id = tokens.get("auth_test", {}).get("team_id") or tokens.get("team_id", "")

    indexed = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        users = await _list_all(client, token, "users.list", "members", {}, 1000)
        user_names = {
            user.get("id"): user.get("real_name") or user.get("name") or user.get("id")
            for user in users
        }
        channels = await _list_all(
            client,
            token,
            "conversations.list",
            "channels",
            {"types": "public_channel,private_channel", "exclude_archived": "true"},
            max_channels,
        )
        for channel in channels:
            channel_id = channel.get("id")
            if not channel_id:
                continue
            messages = await _list_all(
                client,
                token,
                "conversations.history",
                "messages",
                {"channel": channel_id, "inclusive": "true"},
                max_messages_per_channel,
            )
            for message in messages:
                timestamp = message.get("ts")
                body = message.get("text", "").strip()
                if not timestamp or not body:
                    continue
                sender = user_names.get(message.get("user"), message.get("username"))
                channel_name = channel.get("name") or channel_id
                try:
                    occurred_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
                except (TypeError, ValueError):
                    occurred_at = datetime.now(timezone.utc)
                slack_link = (
                    f"https://app.slack.com/client/{team_id}/{channel_id}/p{timestamp.replace('.', '')}"
                    if team_id
                    else None
                )
                text = f"Slack channel: #{channel_name}\nAuthor: {sender or 'Unknown'}\n\n{body}"
                await index_text_document(
                    session,
                    connector,
                    external_id=f"{channel_id}:{timestamp}",
                    title=f"#{channel_name}",
                    text=text,
                    mime_type="text/plain",
                    updated_at=occurred_at,
                    source="Slack",
                    source_url=slack_link,
                    person=sender,
                    extra_metadata={"channel_id": channel_id, "message_ts": timestamp},
                )
                indexed += 1
    connector.last_sync_at = datetime.now(timezone.utc)
    await session.commit()
    return indexed
