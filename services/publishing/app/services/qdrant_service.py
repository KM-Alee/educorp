from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Qdrant collection management, version-safe upsert, and point deletion."""

    def __init__(self) -> None:
        self._client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        """Create the collection and payload indexes if they do not already exist."""
        try:
            self._client.get_collection(self._collection)
            return
        except Exception:
            pass

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )

        for field_name in ("course_id", "version_id", "module_id", "asset_id"):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field_name,
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        logger.info("Created Qdrant collection %s", self._collection)

    def delete_version_points(self, version_id: str) -> int:
        """
        Delete all points belonging to ``version_id``.

        Returns the number of points deleted (best-effort estimate).
        """
        self.ensure_collection()
        result = self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="version_id",
                            match=qmodels.MatchValue(value=version_id),
                        )
                    ]
                )
            ),
        )
        deleted = getattr(result, "deleted_count", 0) or 0
        logger.info("Deleted %s Qdrant points for version %s", deleted, version_id)
        return deleted  # type: ignore[return-value]

    def upsert(self, points: list[qmodels.PointStruct]) -> None:
        """Upsert a batch of points into the collection."""
        if not points:
            return
        self._client.upsert(collection_name=self._collection, points=points)

    def upsert_version_safe(
        self, version_id: str, points: list[qmodels.PointStruct]
    ) -> None:
        """
        Delete existing points for ``version_id`` then upsert fresh points.

        This makes the operation safe on retries — stale embeddings from a
        previous (failed) attempt will not survive.
        """
        self.ensure_collection()
        self.delete_version_points(version_id)
        self.upsert(points)
        logger.info("Upserted %d points for version %s", len(points), version_id)


def build_qdrant_point(
    chunk: dict[str, object], vector: list[float]
) -> qmodels.PointStruct:
    """Build a ``PointStruct`` with the full required payload from a chunk dict."""
    payload = {
        "course_id": str(chunk["course_id"]),
        "version_id": str(chunk["version_id"]),
        "module_id": str(chunk["module_id"]),
        "asset_id": str(chunk["asset_id"]),
        "page_or_slide_number": chunk.get("page_or_slide_number", 0),
        "module_title": str(chunk.get("module_title", "")),
        "asset_title": str(chunk.get("asset_title", "")),
        "chunk_index": chunk.get("chunk_index", 0),
        "quality_score": chunk.get("quality_score", 1.0),
        "source_type": str(chunk.get("source_type", "")),
        "text": str(chunk.get("text", "")),
        "content_sources_used": chunk.get("content_sources_used", []),
        "token_estimate": chunk.get("token_estimate", 0),
    }
    # Use chunk_hash as the stable point ID so retries produce idempotent upserts
    # Qdrant accepts hex IDs but they must be exactly 32 chars (MD5) OR be valid UUIDs.
    # We use UUID5 generated from the chunk signature for a stable, valid ID.
    from uuid import uuid5, NAMESPACE_DNS
    raw_hash = str(chunk.get("chunk_hash", chunk.get("chunk_id", "")))
    point_id = str(uuid5(NAMESPACE_DNS, raw_hash))
    return qmodels.PointStruct(id=point_id, vector=vector, payload=payload)

