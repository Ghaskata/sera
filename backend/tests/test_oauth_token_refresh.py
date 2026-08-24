from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials

import app.crypto as crypto
from app.connectors.google_drive.sync import _persist_refreshed_credentials
from app.models.connector import Connector


@pytest.fixture(autouse=True)
def encryption_key():
    crypto._fernet = Fernet(Fernet.generate_key())
    yield
    crypto._fernet = None


def _fake_connector(token: str) -> Connector:
    connector = Connector(provider="google_drive")
    connector.oauth_tokens_encrypted = crypto.encrypt_tokens(
        {
            "token": token,
            "refresh_token": "refresh-abc",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        }
    )
    return connector


@pytest.mark.asyncio
async def test_persists_new_token_when_credentials_were_refreshed():
    connector = _fake_connector(token="old-token")
    refreshed_creds = Credentials(
        token="new-token",
        refresh_token="refresh-abc",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    session = MagicMock()
    session.commit = AsyncMock()

    await _persist_refreshed_credentials(session, connector, refreshed_creds)

    session.commit.assert_awaited_once()
    stored = crypto.decrypt_tokens(connector.oauth_tokens_encrypted)
    assert stored["token"] == "new-token"


@pytest.mark.asyncio
async def test_does_not_write_or_commit_when_token_is_unchanged():
    connector = _fake_connector(token="same-token")
    unchanged_creds = Credentials(
        token="same-token",
        refresh_token="refresh-abc",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    session = MagicMock()
    session.commit = AsyncMock()

    await _persist_refreshed_credentials(session, connector, unchanged_creds)

    session.commit.assert_not_awaited()
