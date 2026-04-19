from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.enrollments import router as enrollments_router
from app.dependencies import get_redis, get_session, require_internal_service
from app.schemas.enrollment import EnrollmentOut
from app.schemas.internal import EnrollmentCompletionRequest
from app.services.enrollment_service import EnrollmentService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

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
