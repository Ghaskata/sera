from urllib.parse import urlencode

import httpx

from app.config import settings

MICROSOFT_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MICROSOFT_SCOPES = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "User.Read",
    "Calendars.Read",
    "OnlineMeetings.Read",
    "OnlineMeetingTranscript.Read.All",
)


def _authority_path() -> str:
    tenant = settings.microsoft_tenant_id or "common"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"


def build_microsoft_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.microsoft_client_id,
        "response_type": "code",
        "redirect_uri": settings.microsoft_oauth_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(MICROSOFT_SCOPES),
        "state": state,
    }
    return f"{_authority_path()}/authorize?{urlencode(params)}"


async def exchange_microsoft_code(code: str, state: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_authority_path()}/token",
            data={
                "client_id": settings.microsoft_client_id,
                "client_secret": settings.microsoft_client_secret,
                "code": code,
                "redirect_uri": settings.microsoft_oauth_redirect_uri,
                "grant_type": "authorization_code",
                "scope": " ".join(MICROSOFT_SCOPES),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if "access_token" not in payload:
            raise ValueError(payload.get("error_description", "Microsoft OAuth exchange failed"))
        return payload


async def microsoft_profile(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{MICROSOFT_GRAPH_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
