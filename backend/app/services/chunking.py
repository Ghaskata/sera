from app.config import settings

CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50

# Rough token≈word heuristic — good enough for MVP chunk boundaries; not exact BPE.
_WORDS_PER_TOKEN = 0.75


def chunk_text(
    text: str,
    chunk_size_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[str]:
    """Split text into overlapping, deterministic chunks for embedding and retrieval."""
    words = text.split()
    if not words:
        return []

    chunk_size_tokens = chunk_size_tokens or settings.chunk_size_tokens or CHUNK_SIZE_TOKENS
    overlap_tokens = overlap_tokens if overlap_tokens is not None else settings.chunk_overlap_tokens
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens cannot be negative")
    if overlap_tokens >= chunk_size_tokens:
        raise ValueError("overlap_tokens must be smaller than chunk_size_tokens")

    chunk_size_words = max(1, int(chunk_size_tokens * _WORDS_PER_TOKEN))
    overlap_words = max(0, int(overlap_tokens * _WORDS_PER_TOKEN))
    step = max(1, chunk_size_words - overlap_words)

    chunks = []
    for start in range(0, len(words), step):
        piece = words[start : start + chunk_size_words]
        if not piece:
            break
        chunks.append(" ".join(piece))
        if start + chunk_size_words >= len(words):
            break
    return chunks
