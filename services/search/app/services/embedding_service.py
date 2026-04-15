from __future__ import annotations

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError


class EmbeddingService:
    """OpenAI-compatible embedding client for search queries."""

    def __init__(self) -> None:
        self._base_url = settings.openai_base_url.rstrip("/")
        self._api_key = settings.openai_api_key
        self._model = settings.openai_embedding_model

    async def embed_query(self, query: str) -> list[float]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key and self._api_key != "change-me":
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": [query]},
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
        if not data:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Embedding provider returned no data",
                status_code=502,
            )
        return data[0].get("embedding", [])
