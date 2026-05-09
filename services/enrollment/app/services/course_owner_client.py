from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.inter_service_http import inter_service_request
from educorp_common.middleware.correlation import get_correlation_id


class CourseOwnerClient:
    """HTTP client for reading internal course ownership data."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.course_service_url).rstrip("/")

    async def get_course_ownership(self, *, course_id: UUID) -> dict[str, Any]:
        response = await inter_service_request(
            "GET",
            f"{self._base_url}/internal/{course_id}/ownership",
            timeout=10.0,
            headers=self._headers(),
        )
        payload = _parse_payload(response)
        if response.is_error or payload is None or "data" not in payload:
            _raise_remote_error(response, payload, default_code="COURSE_SERVICE_ERROR")
        return dict(payload["data"])

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Internal-Service-Token": settings.internal_service_token,
            "X-Correlation-Id": get_correlation_id(),
        }


def _parse_payload(response: httpx.Response) -> dict[str, Any] | None:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _raise_remote_error(
    response: httpx.Response,
    payload: dict[str, Any] | None,
    *,
    default_code: str,
) -> None:
    if payload and "error" in payload:
        error = payload["error"]
        raise EduCorpError(
            code=str(error.get("code", default_code)),
            message=str(error.get("message", "Upstream service error")),
            status_code=response.status_code,
            details=error.get("details", []),
        )
    raise EduCorpError(
        code=default_code,
        message=f"Upstream service returned {response.status_code}",
        status_code=502,
    )
