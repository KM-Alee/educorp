from __future__ import annotations

from uuid import UUID

import httpx
import structlog

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.middleware.correlation import get_correlation_id

logger = structlog.get_logger()


class CourseActivationClient:
    """HTTP client that calls course service and search service on version activation."""

    def __init__(self) -> None:
        self._course_url = settings.course_service_url.rstrip("/")
        self._search_url = settings.search_service_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Internal-Service-Token": settings.internal_service_token,
            "X-Correlation-Id": get_correlation_id() or "",
        }

    async def activate_course(self, *, course_id: UUID, version_id: UUID) -> None:
        """Tell the course service to activate this version as current."""
        url = f"{self._course_url}/courses/internal/{course_id}/activate-version"
        payload = {"version_id": str(version_id)}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=self._headers())
        if response.is_error:
            body: dict = {}
            try:
                body = response.json()
            except Exception:
                pass
            error = body.get("error", {})
            raise EduCorpError(
                code=str(error.get("code", "COURSE_ACTIVATION_ERROR")),
                message=str(error.get("message", f"Course service returned {response.status_code}")),
                status_code=response.status_code,
            )
        logger.info("Course activated", course_id=str(course_id), version_id=str(version_id))

    async def notify_search_activated(self, *, course_id: UUID) -> None:
        """Notify search service that a course has been activated (best-effort)."""
        url = f"{self._search_url}/search/internal/activate/{course_id}"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(url, headers=self._headers())
            if response.is_error:
                logger.warning(
                    "Search sync notification failed",
                    course_id=str(course_id),
                    status=response.status_code,
                )
        except Exception as exc:
            # Best-effort — do not fail the activation if search sync fails
            logger.warning(
                "Search sync notification error",
                course_id=str(course_id),
                error=str(exc),
            )
