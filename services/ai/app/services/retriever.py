from __future__ import annotations

from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.services.embedding_client import EmbeddingClient


class QdrantRetriever:
    """Retrieve course chunks from Qdrant for AI answers."""

    def __init__(self, qdrant: QdrantClient, embedding_client: EmbeddingClient) -> None:
        self._qdrant = qdrant
        self._embedding = embedding_client
        self._collection = settings.qdrant_collection

    async def retrieve(
        self,
        *,
        course_id: UUID,
        version_id: UUID,
        question: str,
        module_id: UUID | None,
        score_threshold: float | None = None,
    ) -> tuple[list[dict], list[float]]:
        """Retrieve chunks from Qdrant.

        ``score_threshold`` overrides the default ``settings.relevance_threshold``.
        Pass ``0.0`` to fetch all content regardless of similarity (e.g. for
        instructor-tool jobs that need the full course context).
        """
        vector = await self._embedding.embed_query(question)

        must = [
            qmodels.FieldCondition(
                key="course_id",
                match=qmodels.MatchValue(value=str(course_id)),
            ),
            qmodels.FieldCondition(
                key="version_id",
                match=qmodels.MatchValue(value=str(version_id)),
            ),
        ]
        if module_id:
            must.append(
                qmodels.FieldCondition(
                    key="module_id",
                    match=qmodels.MatchValue(value=str(module_id)),
                )
            )

        threshold = score_threshold if score_threshold is not None else settings.relevance_threshold
        results = self._qdrant.query_points(
            collection_name=self._collection,
            query=vector,
            limit=settings.retrieval_top_k,
            query_filter=qmodels.Filter(must=must),
            with_payload=True,
            score_threshold=threshold,
        ).points

        chunks: list[dict] = []
        scores: list[float] = []
        for item in results:
            payload = item.payload or {}
            chunks.append(
                {
                    "chunk_id": str(item.id),
                    "course_id": payload.get("course_id"),
                    "version_id": payload.get("version_id"),
                    "module_id": payload.get("module_id"),
                    "module_title": payload.get("module_title"),
                    "asset_id": payload.get("asset_id"),
                    "asset_title": payload.get("asset_title"),
                    "text": payload.get("text", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "page_number": payload.get("page_or_slide_number"),
                    "section_title": payload.get("section_title"),
                }
            )
            scores.append(float(item.score or 0.0))

        return chunks, scores
