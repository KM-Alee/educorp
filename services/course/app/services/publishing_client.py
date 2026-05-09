from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.config import settings
from app.schemas.publishing import PublishManifest, PublishVersionResponse
from educorp_common.errors import EduCorpError
from educorp_common.inter_service_http import inter_service_request


class PublishingClient:
    """HTTP client for publishing service interactions."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.publishing_service_url).rstrip("/")

    async def create_version(
        self,
        *,
        manifest: PublishManifest,
        auth_header: str | None,
        correlation_id: str | None,
    ) -> PublishVersionResponse:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if auth_header:
            headers["Authorization"] = auth_header
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        response = await inter_service_request(
            "POST",
            f"{self._base_url}/versions",
            timeout=10.0,
            headers=headers,
            json=manifest.model_dump(mode="json"),
        )

        payload = _parse_payload(response)
        if response.is_error or payload is None or "data" not in payload:
            if payload and "error" in payload:
                error = payload["error"]
                raise EduCorpError(
                    code=str(error.get("code", "PUBLISHING_SERVICE_ERROR")),
                    message=str(error.get("message", "Publishing service error")),
                    status_code=response.status_code,
                    details=error.get("details", []),
                )
            raise EduCorpError(
                code="PUBLISHING_SERVICE_ERROR",
                message="Publishing service error",
                status_code=502,
            )

        data = payload["data"]
        return PublishVersionResponse(
            version_id=UUID(data["version_id"]),
            version_number=int(data["version_number"]),
            status=str(data["status"]),
            approval_state=data.get("approval_state"),
            workflow_id=data.get("workflow_id"),
            message=str(data.get("message", "Publishing started")),
        )


def _parse_payload(response: httpx.Response) -> dict[str, Any] | None:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return None
