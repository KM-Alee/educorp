from __future__ import annotations

from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.config import settings
from educorp_common.errors import EduCorpError


class EmbeddingClient:
    """OpenAI-compatible embedding client for queries."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            timeout=settings.embedding_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def embed_query(self, text: str) -> list[float]:
        if settings.ai_provider_mode == "fake":
            seed = sum(ord(ch) for ch in text[:128]) or 1
            return [float((seed + index) % 100) / 100.0 for index in range(16)]
        try:
            response = await self._client.embeddings.create(
                model=settings.embedding_model,
                input=[text],
            )
        except RateLimitError as exc:
            raise EduCorpError(
                code="RATE_LIMIT_EXCEEDED",
                message="Embedding provider rate limit exceeded",
                status_code=429,
            ) from exc
        except APITimeoutError as exc:
            raise EduCorpError(
                code="AI_TIMEOUT",
                message="Embedding request timed out",
                status_code=502,
            ) from exc
        except (APIConnectionError, APIError) as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Embedding provider error",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Unexpected embedding provider error",
                status_code=502,
            ) from exc

        data = getattr(response, "data", None) or []
        if not data:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Embedding provider returned no data",
                status_code=502,
            )
        return _embedding_from_item(data[0])


def _embedding_from_item(item: Any) -> list[float]:
    embedding = getattr(item, "embedding", None)
    return embedding or []
