from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.middleware.correlation import get_correlation_id


class AuthClient:
    """Internal auth client used to enrich notifications with user info."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.auth_service_url).rstrip("/")

    async def get_user_summary(self, *, user_id: UUID) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self._base_url}/internal/users/{user_id}/summary",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Internal-Service-Token": settings.internal_service_token,
                    "X-Correlation-Id": get_correlation_id(),
                },
            )
        payload = _parse_payload(response)
        if response.is_error or payload is None or "data" not in payload:
            _raise_remote_error(response, payload)
        return dict(payload["data"])


def _parse_payload(response: httpx.Response) -> dict[str, Any] | None:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _raise_remote_error(response: httpx.Response, payload: dict[str, Any] | None) -> None:
    if payload and "error" in payload:
        error = payload["error"]
        raise EduCorpError(
            code=str(error.get("code", "AUTH_SERVICE_ERROR")),
            message=str(error.get("message", "Upstream service error")),
            status_code=response.status_code,
            details=error.get("details", []),
        )
    raise EduCorpError(
        code="AUTH_SERVICE_ERROR",
        message=f"Upstream service returned {response.status_code}",
        status_code=502,
    )
