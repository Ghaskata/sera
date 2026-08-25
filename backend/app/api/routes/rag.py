from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.database import async_session_factory
from app.search.rag import query_connected_sources

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQueryRequest(BaseModel):
    workspace_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    source_types: set[str] | None = None


class RagSourceResponse(BaseModel):
    title: str
    source: str | None = None
    date: str | None = None
    person: str | None = None
    url: str | None = None
    drive_link: str | None = None


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSourceResponse]


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    payload: RagQueryRequest,
    x_rag_token: str | None = Header(default=None),
) -> RagQueryResponse:
    """Run a manually authenticated multi-source query for local/admin testing."""
    if not settings.rag_query_token:
        raise HTTPException(
            status_code=503,
            detail="RAG_QUERY_TOKEN is not configured; enable this endpoint explicitly for testing.",
        )
    if x_rag_token != settings.rag_query_token:
        raise HTTPException(status_code=401, detail="Invalid RAG query token")

    async with async_session_factory() as session:
        result = await query_connected_sources(
            session,
            payload.workspace_id,
            payload.question,
            source_types=payload.source_types,
        )
    return RagQueryResponse(
        answer=result.answer,
        sources=[
            RagSourceResponse(
                title=source.title,
                source=source.source,
                date=source.date,
                person=source.person,
                url=source.url,
                drive_link=source.drive_link,
            )
            for source in result.sources
        ],
    )
