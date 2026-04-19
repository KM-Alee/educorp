from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.analytics import router as analytics_router
from app.dependencies import get_session, require_internal_service
from app.repositories.dead_letter_repository import DeadLetterRepository
from app.schemas.admin import DeadLetterMessageOut
from app.services.analytics_service import AnalyticsService
from educorp_common.events import DomainEventBatch, DomainEventIngestResult
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    PaginatedResponse,
    Pagination,
    ResponseMeta,
    SuccessResponse,
)
from educorp_common.telemetry import set_dependency_status

router = APIRouter()

router.include_router(analytics_router)


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

    for dependency, value in checks.items():
        set_dependency_status(service="analytics-service", dependency=dependency, ok=value == "ok")

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
    service = AnalyticsService(session)
    result = await service.ingest_events(payload.events)
    await session.commit()
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/internal/admin/dlq",
    response_model=PaginatedResponse[DeadLetterMessageOut],
)
async def list_dead_letter_messages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    topic: str | None = Query(default=None),
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[DeadLetterMessageOut]:
    repo = DeadLetterRepository(session)
    rows, total = await repo.list_messages(page=page, page_size=page_size, topic=topic)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=[DeadLetterMessageOut.model_validate(row) for row in rows],
        meta=_meta(),
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post(
    "/internal/admin/dlq/{message_id}/replay",
    response_model=SuccessResponse[DeadLetterMessageOut],
)
async def replay_dead_letter_message(
    message_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[DeadLetterMessageOut]:
    from educorp_common.errors import NotFoundError
    from educorp_common.events import normalize_event

    repo = DeadLetterRepository(session)
    service = AnalyticsService(session)
    row = await repo.get_by_id(message_id)
    if row is None:
        raise NotFoundError("Dead-letter message not found")

    await service.ingest_events([normalize_event(dict(row.raw_message))])
    await repo.mark_replayed(row)
    await session.commit()
    return SuccessResponse(data=DeadLetterMessageOut.model_validate(row), meta=_meta())
