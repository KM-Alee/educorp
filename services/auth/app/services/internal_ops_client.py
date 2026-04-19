from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from educorp_common.errors import EduCorpError
from educorp_common.middleware.correlation import get_correlation_id


class InternalOpsClient:
    def __init__(self) -> None:
        self._publishing = settings.publishing_service_url.rstrip("/")
        self._notification = settings.notification_service_url.rstrip("/")
        self._analytics = settings.analytics_service_url.rstrip("/")
        self._enrollment = settings.enrollment_service_url.rstrip("/")

    async def list_workflows(self, *, params: dict[str, str]) -> dict[str, Any]:
        return await self._get(f"{self._publishing}/internal/admin/workflows", params=params)

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return await self._get(f"{self._publishing}/internal/admin/workflows/{workflow_id}")

    async def retry_workflow(self, workflow_id: str) -> dict[str, Any]:
        return await self._post(f"{self._publishing}/internal/admin/workflows/{workflow_id}/retry")

    async def list_notification_dlq(self, *, params: dict[str, str]) -> dict[str, Any]:
        return await self._get(f"{self._notification}/internal/admin/dlq", params=params)

    async def replay_notification_dlq(self, message_id: str) -> dict[str, Any]:
        return await self._post(f"{self._notification}/internal/admin/dlq/{message_id}/replay")

    async def list_analytics_dlq(self, *, params: dict[str, str]) -> dict[str, Any]:
        return await self._get(f"{self._analytics}/internal/admin/dlq", params=params)

    async def replay_analytics_dlq(self, message_id: str) -> dict[str, Any]:
        return await self._post(f"{self._analytics}/internal/admin/dlq/{message_id}/replay")

    async def list_enrollment_audit(self, *, params: dict[str, str]) -> dict[str, Any]:
        return await self._get(f"{self._enrollment}/internal/admin/audit-log", params=params)

    async def _get(self, url: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        return _parse_response(response)

    async def _post(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=self._headers())
        return _parse_response(response)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Internal-Service-Token": settings.internal_service_token,
            "X-Correlation-Id": get_correlation_id(),
        }


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise EduCorpError(
            code="INTERNAL_SERVICE_ERROR",
            message=f"Internal service returned malformed response ({response.status_code})",
            status_code=502,
        ) from exc

    if response.is_error:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        raise EduCorpError(
            code=str(error.get("code", "INTERNAL_SERVICE_ERROR")),
            message=str(error.get("message", f"Internal service returned {response.status_code}")),
            status_code=response.status_code,
            details=error.get("details", []),
        )
    if not isinstance(payload, dict):
        raise EduCorpError(
            code="INTERNAL_SERVICE_ERROR",
            message="Internal service returned unexpected payload",
            status_code=502,
        )
    return payload
