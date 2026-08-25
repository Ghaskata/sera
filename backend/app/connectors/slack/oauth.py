from urllib.parse import urlencode

import httpx

from app.config import settings

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_ACCESS_URL = "https://slack.com/api/oauth.v2.access"
SLACK_AUTH_TEST_URL = "https://slack.com/api/auth.test"
SLACK_BOT_SCOPES = (
    "channels:read",
    "channels:history",
    "groups:read",
    "groups:history",
    "im:history",
    "mpim:history",
    "users:read",
    "team:read",
)


def build_slack_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.slack_client_id,
        "scope": ",".join(SLACK_BOT_SCOPES),
        "redirect_uri": settings.slack_oauth_redirect_uri,
        "state": state,
    }
    return f"{SLACK_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_slack_code(code: str, state: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SLACK_ACCESS_URL,
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": settings.slack_oauth_redirect_uri,
                "state": state,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise ValueError(payload.get("error", "Slack OAuth exchange failed"))
        return payload


async def slack_auth_test(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            SLACK_AUTH_TEST_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise ValueError(payload.get("error", "Slack token validation failed"))
        return payload
