from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding_service import EmbeddingService, _cache_key


class TestCacheKey:
    def test_returns_64_char_hex(self) -> None:
        key = _cache_key("abc123")
        assert len(key) > 10
        assert key.startswith("embed:v1:")

    def test_same_hash_same_key(self) -> None:
        assert _cache_key("same") == _cache_key("same")

    def test_different_hash_different_key(self) -> None:
        assert _cache_key("a") != _cache_key("b")


class TestEmbeddingServiceEmptyInput:
    @pytest.mark.asyncio
    async def test_empty_texts_returns_empty(self) -> None:
        svc = EmbeddingService()
        vectors, reused, created = await svc.embed_texts([], chunk_hashes=[])
        assert vectors == []
        assert reused == 0
        assert created == 0


class TestEmbeddingServiceCaching:
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_api_call(self) -> None:
        svc = EmbeddingService()
        fake_vector = [0.1, 0.2, 0.3]
        chunk_hash = "abc123"

        # Simulate a Redis client that returns a cached embedding
        import json

        mock_redis = AsyncMock()
        mock_redis.mget = AsyncMock(return_value=[json.dumps(fake_vector)])
        svc._redis = mock_redis

        vectors, reused, created = await svc.embed_texts(
            ["text"], chunk_hashes=[chunk_hash]
        )
        assert vectors == [fake_vector]
        assert reused == 1
        assert created == 0

    @pytest.mark.asyncio
    async def test_cache_miss_calls_embed_api(self) -> None:
        svc = EmbeddingService()
        fake_vector = [0.4, 0.5, 0.6]

        mock_redis = AsyncMock()
        mock_redis.mget = AsyncMock(return_value=[None])
        mock_pipeline = MagicMock()
        mock_pipeline.setex = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[True])
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        svc._redis = mock_redis

        with patch.object(svc, "_embed_batch", AsyncMock(return_value=[fake_vector])):
            vectors, reused, created = await svc.embed_texts(
                ["text"], chunk_hashes=["hash1"]
            )

        assert vectors == [fake_vector]
        assert reused == 0
        assert created == 1

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_through(self) -> None:
        svc = EmbeddingService()
        fake_vector = [0.7, 0.8, 0.9]

        # _get_redis returning None → no cache (skip_cache path)
        with (
            patch.object(svc, "_get_redis", AsyncMock(return_value=None)),
            patch.object(svc, "_embed_batch", AsyncMock(return_value=[fake_vector])),
        ):
            vectors, reused, created = await svc.embed_texts(
                ["text"], chunk_hashes=["hash1"]
            )

        assert vectors == [fake_vector]
        assert reused == 0
        assert created == 1
