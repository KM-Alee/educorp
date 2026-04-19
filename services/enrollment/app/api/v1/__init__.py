from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.enrollments import router as enrollments_router
from app.dependencies import get_redis, get_session, require_internal_service
from app.schemas.enrollment import EnrollmentOut
from app.schemas.internal import EnrollmentAuditOut, EnrollmentCompletionRequest
from app.repositories.enrollment_audit_repository import EnrollmentAuditRepository
from app.services.enrollment_service import EnrollmentService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    PaginatedResponse,
    Pagination,
    ResponseMeta,
    SuccessResponse,
)
from educorp_common.telemetry import set_dependency_status

router = APIRouter()

router.include_router(enrollments_router)


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
    redis: Redis = Depends(get_redis),
) -> dict[str, object]:
    """Readiness probe — verify required dependencies are reachable."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    for dependency, value in checks.items():
        set_dependency_status(service="enrollment-service", dependency=dependency, ok=value == "ok")

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


@router.post(
    "/internal/enrollments/{enrollment_id}/complete",
    response_model=SuccessResponse[EnrollmentOut],
    status_code=status.HTTP_200_OK,
)
async def mark_enrollment_completed(
    enrollment_id: UUID,
    payload: EnrollmentCompletionRequest,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentOut]:
    service = EnrollmentService(session, redis)
    try:
        result = await service.mark_completed(
            enrollment_id=enrollment_id,
            completed_at=payload.completed_at,
            correlation_id=get_correlation_id(),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/internal/admin/audit-log",
    response_model=PaginatedResponse[EnrollmentAuditOut],
)
async def list_enrollment_audit_log(
    page: int = 1,
    page_size: int = 20,
    actor_id: UUID | None = None,
    action: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[EnrollmentAuditOut]:
    repo = EnrollmentAuditRepository(session)
    rows, total = await repo.list_entries(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=[EnrollmentAuditOut.model_validate(row) for row in rows],
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
