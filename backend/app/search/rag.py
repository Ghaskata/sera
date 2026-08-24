import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chunk import Chunk
from app.models.query_log import QueryLog
from app.services.embeddings import embed_text
from app.services.llm import generate_answer

NO_CONTEXT_ANSWER = "I couldn't find relevant information in your connected sources for that question."


@dataclass
class Source:
    title: str
    drive_link: str | None


@dataclass
class RagResult:
    answer: str
    sources: list[Source]


async def answer_question(session: AsyncSession, workspace_id: uuid.UUID, question: str) -> RagResult:
    query_vector = await embed_text(question)

    distance = Chunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(Chunk, distance.label("distance"))
        .where(Chunk.workspace_id == workspace_id)
        .order_by(distance)
        .limit(settings.rag_top_k)
    )
    rows = (await session.execute(stmt)).all()

    relevant = [(chunk, 1 - dist) for chunk, dist in rows if (1 - dist) >= settings.rag_min_similarity]

    if not relevant:
        result = RagResult(answer=NO_CONTEXT_ANSWER, sources=[])
    else:
        answer = await generate_answer(question, [chunk.text for chunk, _ in relevant])
        seen = set()
        sources = []
        for chunk, _ in relevant:
            title = chunk.chunk_metadata.get("title", "source")
            if title in seen:
                continue
            seen.add(title)
            sources.append(Source(title=title, drive_link=chunk.chunk_metadata.get("drive_link")))
        result = RagResult(answer=answer, sources=sources)

    session.add(
        QueryLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            question=question,
            answer=result.answer,
            sources=[{"title": s.title, "drive_link": s.drive_link} for s in result.sources],
        )
    )
    await session.commit()
    return result
