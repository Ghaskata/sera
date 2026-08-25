import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_IDENTITY_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
)
SCOPES_BY_PROVIDER = {
    "google_drive": (*GOOGLE_IDENTITY_SCOPES, "https://www.googleapis.com/auth/drive.readonly"),
    "google_gmail": (*GOOGLE_IDENTITY_SCOPES, "https://www.googleapis.com/auth/gmail.readonly"),
    "google_calendar": (*GOOGLE_IDENTITY_SCOPES, "https://www.googleapis.com/auth/calendar.readonly"),
    "google_meet": (*GOOGLE_IDENTITY_SCOPES, "https://www.googleapis.com/auth/meetings.space.readonly"),
    "google_keep": (*GOOGLE_IDENTITY_SCOPES, "https://www.googleapis.com/auth/keep.readonly"),
}
# Backwards-compatible name used by the original Drive connector.
SCOPES = list(SCOPES_BY_PROVIDER["google_drive"])


def scopes_for_provider(provider: str) -> list[str]:
    try:
        return list(SCOPES_BY_PROVIDER[provider])
    except KeyError as exc:
        raise ValueError(f"Unsupported Google connector provider: {provider}") from exc


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }


def build_authorization_url(state: str, provider: str = "google_drive") -> str:
    flow = Flow.from_client_config(_client_config(), scopes=scopes_for_provider(provider), state=state)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code_for_tokens(code: str, state: str, provider: str = "google_drive") -> dict:
    flow = Flow.from_client_config(_client_config(), scopes=scopes_for_provider(provider), state=state)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    flow.fetch_token(code=code)
    return credentials_to_dict(flow.credentials)


def credentials_to_dict(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


async def fetch_google_profile(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def credentials_from_dict(data: dict) -> Credentials:
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
