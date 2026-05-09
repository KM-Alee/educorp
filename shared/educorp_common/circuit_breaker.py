from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from educorp_common.errors import CircuitBreakerOpenError

T = TypeVar("T")


class AsyncCircuitBreaker:
    """Minimal async circuit breaker (fail-fast after repeated upstream failures)."""

    def __init__(
        self,
        *,
        fail_max: int = 5,
        reset_timeout_seconds: float = 30.0,
    ) -> None:
        self._fail_max = fail_max
        self._reset_timeout_seconds = reset_timeout_seconds
        self._failures = 0
        self._state: str = "closed"
        self._opened_at_monotonic: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        await self._before_attempt()
        try:
            result = await func()
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                raise
            await self._record_failure()
            raise
        await self._record_success()
        return result

    async def _before_attempt(self) -> None:
        async with self._lock:
            if self._state == "open":
                assert self._opened_at_monotonic is not None
                if time.monotonic() - self._opened_at_monotonic >= self._reset_timeout_seconds:
                    self._state = "half_open"
                else:
                    raise CircuitBreakerOpenError()

    async def _record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at_monotonic = None

    async def _record_failure(self) -> None:
        async with self._lock:
            if self._state == "half_open":
                self._state = "open"
                self._opened_at_monotonic = time.monotonic()
                self._failures = self._fail_max
                return
            self._failures += 1
            if self._failures >= self._fail_max:
                self._state = "open"
                self._opened_at_monotonic = time.monotonic()
