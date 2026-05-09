from __future__ import annotations

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.inter_service_http import inter_service_request


class EmbeddingService:
    """OpenAI-compatible embedding client for search queries."""

    def __init__(self) -> None:
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._api_key = settings.embedding_api_key
        self._model = settings.embedding_model

    async def embed_query(self, query: str) -> list[float]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key and self._api_key != "change-me":
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await inter_service_request(
                "POST",
                f"{self._base_url}/embeddings",
                timeout=30.0,
                headers=headers,
                json={"model": self._model, "input": [query]},
            )
        except httpx.HTTPStatusError as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message=f"Embedding provider error: HTTP {exc.response.status_code}",
                status_code=502,
            ) from exc

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
