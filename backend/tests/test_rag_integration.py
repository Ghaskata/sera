import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.chunk import Chunk, EMBEDDING_DIM
from app.models.document import Document
from app.search import rag


def _vector(seed: float) -> list[float]:
    # Deterministic pseudo-embedding: mostly `seed`, distinguishable per chunk.
    return [seed] * EMBEDDING_DIM


@pytest.mark.asyncio
async def test_answer_question_retrieves_and_cites_the_matching_chunk(db_session):
    workspace_id = uuid.uuid4()
    other_workspace_id = uuid.uuid4()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        connector_id=uuid.uuid4(),
        external_id="drive-file-1",
        title="Q3 Roadmap.pdf",
        mime_type="application/pdf",
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db_session.add(document)

    # The chunk that actually answers the question — embedding matches the query exactly.
    target_chunk = Chunk(
        id=uuid.uuid4(),
        document_id=document.id,
        workspace_id=workspace_id,
        text="The Q3 roadmap decided to migrate authentication to JWT.",
        embedding=_vector(1.0),
        chunk_metadata={"title": "Q3 Roadmap.pdf", "drive_link": "https://drive.google.com/file/d/xyz"},
    )
    # An unrelated chunk, far away in embedding space — should not be selected.
    unrelated_chunk = Chunk(
        id=uuid.uuid4(),
        document_id=document.id,
        workspace_id=workspace_id,
        text="The office lunch menu for Friday is pizza.",
        embedding=_vector(-1.0),
        chunk_metadata={"title": "Lunch Menu.pdf", "drive_link": "https://drive.google.com/file/d/lunch"},
    )
    # A chunk that would match perfectly but belongs to a different workspace.
    other_workspace_chunk = Chunk(
        id=uuid.uuid4(),
        document_id=document.id,
        workspace_id=other_workspace_id,
        text="Irrelevant — belongs to a different workspace.",
        embedding=_vector(1.0),
        chunk_metadata={"title": "Other Workspace Doc.pdf", "drive_link": None},
    )
    db_session.add_all([target_chunk, unrelated_chunk, other_workspace_chunk])
    await db_session.commit()

    with (
        patch.object(rag, "embed_text", new=AsyncMock(return_value=_vector(1.0))),
        patch.object(rag, "generate_answer", new=AsyncMock(return_value="We migrated auth to JWT in Q3.")) as mock_generate,
    ):
        result = await rag.answer_question(db_session, workspace_id, "What did we decide about authentication?")

    assert result.answer == "We migrated auth to JWT in Q3."
    assert len(result.sources) == 1
    assert result.sources[0].title == "Q3 Roadmap.pdf"
    assert result.sources[0].drive_link == "https://drive.google.com/file/d/xyz"

    # only the matching chunk's text should have been sent to the LLM as context
    mock_generate.assert_awaited_once()
    args, _ = mock_generate.call_args
    assert args[1] == [target_chunk.text]


@pytest.mark.asyncio
async def test_answer_question_returns_no_context_message_when_nothing_clears_the_similarity_floor(db_session):
    workspace_id = uuid.uuid4()
    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        connector_id=uuid.uuid4(),
        external_id="drive-file-2",
        title="Unrelated.pdf",
        mime_type="application/pdf",
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db_session.add(document)
    db_session.add(
        Chunk(
            id=uuid.uuid4(),
            document_id=document.id,
            workspace_id=workspace_id,
            text="Completely unrelated content.",
            embedding=_vector(-1.0),
            chunk_metadata={"title": "Unrelated.pdf"},
        )
    )
    await db_session.commit()

    with (
        patch.object(rag, "embed_text", new=AsyncMock(return_value=_vector(1.0))),
        patch.object(rag, "generate_answer", new=AsyncMock()) as mock_generate,
    ):
        result = await rag.answer_question(db_session, workspace_id, "What did we decide about authentication?")

    assert result.answer == rag.NO_CONTEXT_ANSWER
    assert result.sources == []
    mock_generate.assert_not_awaited()
