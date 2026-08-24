import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    prompt = (
        "You are Sera, an assistant that answers questions using only the provided context. "
        "If the context does not contain the answer, say you don't have enough information.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    )

    url = _GEMINI_URL.format(model=settings.gemini_model)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
