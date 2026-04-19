from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from redis.asyncio import Redis


class RedisLock:
    """Simple Redis distributed lock with a token check on release."""

    def __init__(self, redis: Redis, key: str, ttl_seconds: int = 30) -> None:
        self._redis = redis
        self._key = key
        self._ttl_seconds = ttl_seconds
        self._token = uuid4().hex

    async def acquire(self, timeout_seconds: float = 5.0, retry_delay: float = 0.1) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            acquired = await self._redis.set(
                self._key,
                self._token,
                nx=True,
                ex=self._ttl_seconds,
            )
            if acquired:
                return True
            await asyncio.sleep(retry_delay)
        return False

    async def release(self) -> None:
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] "
            "then return redis.call('del', KEYS[1]) else return 0 end"
        )
        await self._redis.eval(script, 1, self._key, self._token)
