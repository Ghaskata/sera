import pytest

from app.config import settings
from app.services.chunking import chunk_text
from app.services.vector_store import get_vector_store


def test_chunking_respects_explicit_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(30))
    chunks = chunk_text(text, chunk_size_tokens=8, overlap_tokens=3)
    assert len(chunks) > 1
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_chunking_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size_tokens=10, overlap_tokens=10)


def test_pgvector_is_the_default_store(monkeypatch):
    monkeypatch.setattr(settings, "vector_store_backend", "pgvector")
    assert get_vector_store() is None
