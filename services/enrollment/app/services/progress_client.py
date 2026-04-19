from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.middleware.correlation import get_correlation_id


class ProgressClient:
    """HTTP client for initializing and querying progress state."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.progress_service_url).rstrip("/")

    async def initialize_progress(
        self,
        *,
        enrollment_id: UUID,
        student_id: UUID,
        student_name: str,
        course_context: dict[str, Any],
        enrolled_at: datetime,
    ) -> None:
        payload = {
            "enrollment_id": str(enrollment_id),
            "student_id": str(student_id),
            "student_name": student_name,
            "course_id": course_context["course_id"],
            "course_title": course_context["title"],
            "modules": course_context["modules"],
            "enrolled_at": enrolled_at.isoformat(),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self._base_url}/internal/init",
                json=payload,
                headers=self._headers(),
            )
        parsed = _parse_payload(response)
        if response.is_error or parsed is None or "data" not in parsed:
            _raise_remote_error(response, parsed, default_code="PROGRESS_INIT_ERROR")

    async def get_progress_summary(self, *, enrollment_id: UUID) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self._base_url}/internal/enrollments/{enrollment_id}/summary",
                headers=self._headers(),
            )
        if response.status_code == 404:
            return None
        parsed = _parse_payload(response)
        if response.is_error or parsed is None or "data" not in parsed:
            _raise_remote_error(response, parsed, default_code="PROGRESS_SUMMARY_ERROR")
        return dict(parsed["data"])

    async def cancel_progress(self, *, enrollment_id: UUID) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self._base_url}/internal/enrollments/{enrollment_id}/cancel",
                headers=self._headers(),
            )
        parsed = _parse_payload(response)
        if response.is_error or parsed is None or "data" not in parsed:
            _raise_remote_error(response, parsed, default_code="PROGRESS_CANCEL_ERROR")

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
