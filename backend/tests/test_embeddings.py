from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.embeddings import embed_text, embed_texts


@pytest.mark.asyncio
async def test_embed_text_calls_gemini_and_returns_vector():
    fake_response = httpx.Response(200, json={"embedding": {"values": [0.1, 0.2, 0.3]}})
    fake_response._request = httpx.Request("POST", "http://fake/embedContent")

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake_response)) as mock_post:
        vector = await embed_text("hello world")

    assert vector == [0.1, 0.2, 0.3]
    mock_post.assert_awaited_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["content"]["parts"][0]["text"] == "hello world"


@pytest.mark.asyncio
async def test_embed_texts_embeds_each_text_in_order():
    responses = [
        httpx.Response(200, json={"embedding": {"values": [1.0]}}),
        httpx.Response(200, json={"embedding": {"values": [2.0]}}),
    ]
    for r in responses:
        r._request = httpx.Request("POST", "http://fake/embedContent")

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=responses)):
        vectors = await embed_texts(["a", "b"])

    assert vectors == [[1.0], [2.0]]


@pytest.mark.asyncio
async def test_embed_text_retries_on_failure_then_succeeds():
    ok = httpx.Response(200, json={"embedding": {"values": [0.5]}})
    ok._request = httpx.Request("POST", "http://fake/embedContent")

    with patch(
        "httpx.AsyncClient.post",
        new=AsyncMock(side_effect=[httpx.ConnectError("boom"), ok]),
    ) as mock_post:
        vector = await embed_text("retry me")

    assert vector == [0.5]
    assert mock_post.await_count == 2
