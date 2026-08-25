import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorMatch:
    chunk_id: str
    similarity: float


class VectorStore(Protocol):
    async def upsert_chunks(self, records: list[dict[str, Any]]) -> None: ...

    async def delete_document(self, document_id: str, workspace_id: str) -> None: ...

    async def query(
        self,
        embedding: list[float],
        workspace_id: str,
        top_k: int,
        source_types: set[str] | None = None,
    ) -> list[VectorMatch]: ...


class ChromaVectorStore:
    def __init__(self) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _metadata(record: dict[str, Any]) -> dict[str, Any]:
        metadata = {
            "workspace_id": record["workspace_id"],
            "document_id": record["document_id"],
            "source": record.get("source", ""),
            "title": record.get("title", ""),
            "url": record.get("url", ""),
        }
        return {key: value for key, value in metadata.items() if value is not None}

    async def upsert_chunks(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        await asyncio.to_thread(
            self.collection.upsert,
            ids=[record["id"] for record in records],
            embeddings=[record["embedding"] for record in records],
            documents=[record["text"] for record in records],
            metadatas=[self._metadata(record) for record in records],
        )

    async def delete_document(self, document_id: str, workspace_id: str) -> None:
        await asyncio.to_thread(
            self.collection.delete,
            where={"$and": [{"workspace_id": workspace_id}, {"document_id": document_id}]},
        )

    async def query(
        self,
        embedding: list[float],
        workspace_id: str,
        top_k: int,
        source_types: set[str] | None = None,
    ) -> list[VectorMatch]:
        where: dict[str, Any] = {"workspace_id": workspace_id}
        if source_types:
            where = {"$and": [where, {"source": {"$in": sorted(source_types)}}]}
        result = await asyncio.to_thread(
            self.collection.query,
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            VectorMatch(chunk_id=str(chunk_id), similarity=max(0.0, min(1.0, 1.0 - float(distance))))
            for chunk_id, distance in zip(ids, distances)
        ]


class PineconeVectorStore:
    def __init__(self) -> None:
        from pinecone import Pinecone

        if not settings.pinecone_api_key or not settings.pinecone_index_host:
            raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX_HOST are required")
        self.client = Pinecone(api_key=settings.pinecone_api_key)
        self.index = self.client.Index(host=settings.pinecone_index_host)

    @staticmethod
    def _metadata(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "workspace_id": record["workspace_id"],
            "document_id": record["document_id"],
            "source": record.get("source", ""),
            "title": record.get("title", ""),
            "url": record.get("url", ""),
        }

    async def upsert_chunks(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        vectors = [
            {
                "id": record["id"],
                "values": record["embedding"],
                "metadata": self._metadata(record),
            }
            for record in records
        ]
        await asyncio.to_thread(
            self.index.upsert,
            vectors=vectors,
            namespace=settings.pinecone_namespace,
        )

    async def delete_document(self, document_id: str, workspace_id: str) -> None:
        await asyncio.to_thread(
            self.index.delete,
            namespace=settings.pinecone_namespace,
            filter={
                "workspace_id": {"$eq": workspace_id},
                "document_id": {"$eq": document_id},
            },
        )

    async def query(
        self,
        embedding: list[float],
        workspace_id: str,
        top_k: int,
        source_types: set[str] | None = None,
    ) -> list[VectorMatch]:
        metadata_filter: dict[str, Any] = {"workspace_id": {"$eq": workspace_id}}
        if source_types:
            metadata_filter["source"] = {"$in": sorted(source_types)}
        response = await asyncio.to_thread(
            self.index.query,
            vector=embedding,
            top_k=top_k,
            namespace=settings.pinecone_namespace,
            filter=metadata_filter,
            include_metadata=False,
        )
        matches = response.get("matches", []) if isinstance(response, dict) else getattr(response, "matches", [])
        output = []
        for match in matches:
            chunk_id = match.get("id") if isinstance(match, dict) else getattr(match, "id", None)
            score = match.get("score") if isinstance(match, dict) else getattr(match, "score", 0.0)
            if chunk_id is not None:
                output.append(VectorMatch(chunk_id=str(chunk_id), similarity=float(score or 0.0)))
        return output


def get_vector_store() -> VectorStore | None:
    backend = settings.vector_store_backend.lower()
    if backend in {"", "pgvector", "postgres", "postgresql"}:
        return None
    if backend == "chroma":
        try:
            return ChromaVectorStore()
        except ImportError as exc:
            raise RuntimeError("Install backend/requirements-vector.txt for Chroma support") from exc
    if backend == "pinecone":
        try:
            return PineconeVectorStore()
        except ImportError as exc:
            raise RuntimeError("Install backend/requirements-vector.txt for Pinecone support") from exc
    raise ValueError(f"Unsupported VECTOR_STORE_BACKEND: {settings.vector_store_backend}")
