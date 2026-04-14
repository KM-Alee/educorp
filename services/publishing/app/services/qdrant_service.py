from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings


class QdrantService:
    """Qdrant collection bootstrap and upsert."""

    def __init__(self) -> None:
        self._client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
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

        for field in ("course_id", "version_id", "module_id", "asset_id"):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

    def upsert(self, points: list[qmodels.PointStruct]) -> None:
        if not points:
            return
        self._client.upsert(collection_name=self._collection, points=points)
