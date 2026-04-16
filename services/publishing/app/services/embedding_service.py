from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Iterable

import httpx
import redis.asyncio as aioredis

from app.config import settings
from educorp_common.errors import EduCorpError

logger = logging.getLogger(__name__)


def _cache_key(chunk_hash: str) -> str:
    """Redis key for a cached embedding vector."""
    provider = "openai"
    model = settings.embedding_model
    suffix = hashlib.sha256(f"{chunk_hash}:{provider}:{model}".encode()).hexdigest()
    return f"embed:v1:{suffix}"


class EmbeddingService:
    """
    OpenAI-compatible embedding client with Redis-backed per-chunk caching.

    Cache key: SHA-256( chunk_hash + ":" + provider + ":" + model )
    TTL: ``settings.embedding_cache_ttl_seconds`` (default 7 days)
    """

    def __init__(self) -> None:
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._api_key = settings.embedding_api_key
        self._model = settings.embedding_model
        self._batch_size = settings.embedding_batch_size
        self._ttl = settings.embedding_cache_ttl_seconds
        self._redis: aioredis.Redis | None = None  # type: ignore[type-arg]

    async def _get_redis(self) -> aioredis.Redis | None:  # type: ignore[type-arg]
        if self._redis is not None:
            return self._redis
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=False)
            await client.ping()
            self._redis = client
            return self._redis
        except Exception as exc:
            logger.warning("Redis unavailable; embedding cache disabled: %s", exc)
            return None

    async def embed_texts(
        self,
        texts: list[str],
        chunk_hashes: list[str] | None = None,
    ) -> tuple[list[list[float]], int, int]:
        """
        Embed a list of texts, using the cache when possible.

        Args:
            texts: Text strings to embed.
            chunk_hashes: Per-text chunk hashes for cache keying.
                          Pass ``None`` to skip caching.

        Returns:
            ``(vectors, reused_count, created_count)``
        """
        if not texts:
            return [], 0, 0

        use_cache = chunk_hashes is not None and len(chunk_hashes) == len(texts)
        redis_client = await self._get_redis() if use_cache else None

        vectors: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        reused = 0

        # ── Cache lookup ─────────────────────────────────────────────────────
        if redis_client and chunk_hashes:
            keys = [_cache_key(h) for h in chunk_hashes]
            cached_values = await redis_client.mget(*keys)  # type: ignore[arg-type]
            for i, raw in enumerate(cached_values):
                if raw is not None:
                    try:
                        vectors[i] = json.loads(raw)
                        reused += 1
                    except json.JSONDecodeError:
                        uncached_indices.append(i)
                else:
                    uncached_indices.append(i)
        else:
            uncached_indices = list(range(len(texts)))

        # ── Batch embed uncached texts ─────────────────────────────────────
        created = 0
        if uncached_indices:
            uncached_texts = [texts[i] for i in uncached_indices]
            new_vectors: list[list[float]] = []
            for batch in _batched(uncached_texts, self._batch_size):
                new_vectors.extend(await self._embed_batch_with_retry(batch))
            created = len(new_vectors)

            for local_idx, global_idx in enumerate(uncached_indices):
                vectors[global_idx] = new_vectors[local_idx]

            # Store in cache
            if redis_client and chunk_hashes:
                pipe = redis_client.pipeline()
                for local_idx, global_idx in enumerate(uncached_indices):
                    key = _cache_key(chunk_hashes[global_idx])
                    pipe.setex(key, self._ttl, json.dumps(new_vectors[local_idx]))
                await pipe.execute()

        final: list[list[float]] = [v for v in vectors if v is not None]
        return final, reused, created

    async def _embed_batch_with_retry(
        self, batch: list[str], max_retries: int = 3
    ) -> list[list[float]]:
        for attempt in range(max_retries):
            try:
                return await self._embed_batch(batch)
            except EduCorpError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning("Embedding batch failed (attempt %d); retrying in %ds", attempt + 1, wait)
                await asyncio.sleep(wait)
        raise EduCorpError(
            code="AI_PROVIDER_ERROR",
            message="Embedding provider failed after retries",
            status_code=502,
        )

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key and self._api_key != "change-me":
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": batch},
                headers=headers,
            )

        if response.is_error:
            logger.error("Embedding API error %s: %s", response.status_code, response.text[:300])
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message=f"Embedding provider error: HTTP {response.status_code}",
                status_code=502,
            )

        payload = response.json()
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        return [item.get("embedding", []) for item in data]


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    size = max(1, size)
    for i in range(0, len(items), size):
        yield items[i : i + size]

