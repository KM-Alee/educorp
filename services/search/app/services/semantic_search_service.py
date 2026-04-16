from __future__ import annotations

from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.repositories.course_search_repository import CourseSearchRepository
from app.schemas.search import SemanticChunkResult
from app.services.embedding_service import EmbeddingService
from educorp_common.errors import EduCorpError


class SemanticSearchService:
    """Semantic search over PUBLISHED, activated course chunks."""

    def __init__(self, repo: CourseSearchRepository) -> None:
        self._repo = repo
        self._qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._collection = settings.qdrant_collection

    async def search(
        self,
        *,
        course_id: UUID,
        query: str,
        top_k: int,
        module_id: UUID | None,
    ) -> list[SemanticChunkResult]:
        version_id = await self._repo.get_ready_version_id(course_id)
        if version_id is None:
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not active and ready for semantic search",
                status_code=409,
            )

        vector = await EmbeddingService().embed_query(query)

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

        results = self._qdrant.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
            query_filter=qmodels.Filter(must=must),
        ).points

        chunks: list[SemanticChunkResult] = []
        for item in results:
            payload = item.payload or {}
            p_module_id = UUID(payload["module_id"])
            p_asset_id = UUID(payload["asset_id"])
            p_course_id = UUID(payload.get("course_id", str(course_id)))
            p_version_id = UUID(payload.get("version_id", str(version_id)))
            chunks.append(
                SemanticChunkResult(
                    chunk_id=str(item.id),
                    course_id=p_course_id,
                    version_id=p_version_id,
                    text=str(payload.get("text", "")),
                    score=float(item.score),
                    module_id=p_module_id,
                    module_title=payload.get("module_title"),
                    asset_id=p_asset_id,
                    asset_title=payload.get("asset_title"),
                    page_or_slide_number=payload.get("page_or_slide_number"),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    quality_score=payload.get("quality_score"),
                )
            )

        return chunks
