from __future__ import annotations

from typing import Iterable

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError


class EmbeddingService:
    """OpenAI-compatible embedding client."""

    def __init__(self) -> None:
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._api_key = settings.embedding_api_key
        self._model = settings.embedding_model
        self._batch_size = settings.embedding_batch_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for batch in _batched(texts, self._batch_size):
            embeddings.extend(await self._embed_batch(batch))
        return embeddings

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key and self._api_key != "change-me":
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": batch},
                headers=headers,
            )

        if response.is_error:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Embedding provider error",
                status_code=502,
            )

        payload = response.json()
        data = payload.get("data", [])
        data_sorted = sorted(data, key=lambda item: item.get("index", 0))
        return [item.get("embedding", []) for item in data_sorted]


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    size = max(1, size)
    for i in range(0, len(items), size):
        yield items[i : i + size]
