import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

_GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def embed_text(text: str) -> list[float]:
    url = _GEMINI_EMBED_URL.format(model=settings.gemini_embed_model)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json={"content": {"parts": [{"text": text}]}},
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    # Sequential calls are fine at MVP volume; switch to batchEmbedContents if this becomes a bottleneck.
    return [await embed_text(t) for t in texts]
