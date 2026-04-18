from __future__ import annotations

import time
from uuid import uuid4

from redis.asyncio import Redis

from educorp_common.errors import EduCorpError


class RateLimiter:
    """Redis sorted-set sliding window rate limiter."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def enforce(self, *, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        member = f"{now}:{uuid4()}"
        oldest = now - window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, oldest)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        _, _, count, _ = await pipe.execute()

        if int(count) > limit:
            raise EduCorpError(
                code="RATE_LIMIT_EXCEEDED",
                message="Rate limit exceeded",
                status_code=429,
            )
