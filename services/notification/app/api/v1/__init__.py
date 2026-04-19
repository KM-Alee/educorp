from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.notifications import router as notifications_router
from app.dependencies import get_session, require_internal_service
from app.services.notification_service import NotificationService
from educorp_common.events import DomainEventBatch, DomainEventIngestResult
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter()

router.include_router(notifications_router)


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Readiness probe — verify required dependencies are reachable."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


@router.post(
    "/internal/events",
    response_model=SuccessResponse[DomainEventIngestResult],
)
async def ingest_domain_events(
    payload: DomainEventBatch,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[DomainEventIngestResult]:
    service = NotificationService(session)
    result = await service.ingest_events(payload.events)
    await session.commit()
    return SuccessResponse(data=result, meta=_meta())
