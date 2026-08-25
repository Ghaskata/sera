import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.google_workspace import sync
from app.models.connector import Connector


def test_gmail_body_decoder_handles_unpadded_urlsafe_data():
    encoded = "SGVsbG8gU2VyYQ"
    assert sync._decode_base64url(encoded) == "Hello Sera"


def test_gmail_message_body_walks_nested_parts():
    payload = {
        "parts": [
            {"body": {"data": "SGVsbG8="}},
            {"parts": [{"body": {"data": "V29ybGQ="}}]},
        ]
    }
    assert sync._parse_message_body(payload) == "Hello\nWorld"


@pytest.mark.asyncio
async def test_gmail_sync_indexes_messages_as_cited_documents():
    connector = Connector(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="google_gmail",
        oauth_tokens_encrypted=b"encrypted",
    )
    session = MagicMock()
    session.commit = AsyncMock()

    service = MagicMock()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": "message-1"}],
    }
    service.users().messages().get().execute.return_value = {
        "id": "message-1",
        "threadId": "thread-1",
        "internalDate": "1724500000000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Payment API decision"},
                {"name": "From", "value": "rahul@example.com"},
            ],
            "body": {"data": "VGhlIHRlYW0gY2hvc2UgQVBJIHYyLg=="},
        },
    }

    fake_creds = MagicMock()
    with (
        patch.object(sync, "_credentials_for_connector", new=AsyncMock(return_value=fake_creds)),
        patch.object(sync, "_build_service", return_value=service),
        patch.object(sync, "index_text_document", new=AsyncMock()) as index_document,
    ):
        indexed = await sync.run_gmail_sync(session, connector, max_messages=10)

    assert indexed == 1
    index_document.assert_awaited_once()
    kwargs = index_document.await_args.kwargs
    assert kwargs["external_id"] == "message-1"
    assert kwargs["source"] == "Gmail"
    assert kwargs["title"] == "Payment API decision"
    assert kwargs["person"] == "rahul@example.com"
    assert "API v2" in kwargs["text"]
    session.commit.assert_awaited_once()
