from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from educorp_common.circuit_breaker import AsyncCircuitBreaker

_breakers: dict[str, AsyncCircuitBreaker] = {}


def _breaker_key_for_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "unknown-host"
    port = parsed.port
    if port:
        return f"{host}:{port}"
    return host


def _get_breaker(url: str) -> AsyncCircuitBreaker:
    key = _breaker_key_for_url(url)
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker()
    return _breakers[key]


def reset_inter_service_breakers() -> None:
    """Clear breaker state (for tests)."""

    _breakers.clear()


async def inter_service_request(
    method: str,
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    json: Any | None = None,
    params: dict[str, Any] | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    """Perform an HTTP call with per-host circuit breaking."""

    breaker = _get_breaker(url)

    async def _call() -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
                content=content,
            )
        if response.status_code >= 500:
            request = response.request
            raise httpx.HTTPStatusError(
                f"Server error {response.status_code}",
                request=request,
                response=response,
            )
        return response

    return await breaker.call(_call)
