from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.progress import router as progress_router
from app.dependencies import get_session, require_internal_service
from app.schemas.internal import ProgressInitRequest, ProgressInitResponse, ProgressSummaryResponse
from app.services.progress_service import ProgressService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter()

router.include_router(progress_router)


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
    "/internal/init",
    response_model=SuccessResponse[ProgressInitResponse],
    status_code=status.HTTP_201_CREATED,
)
async def initialize_progress(
    payload: ProgressInitRequest,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressInitResponse]:
    service = ProgressService(session)
    try:
        result = await service.initialize_progress(
            payload=payload,
            correlation_id=get_correlation_id(),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/internal/enrollments/{enrollment_id}/summary",
    response_model=SuccessResponse[ProgressSummaryResponse],
)
async def get_progress_summary(
    enrollment_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressSummaryResponse]:
    service = ProgressService(session)
    result = await service.get_progress_summary(enrollment_id=enrollment_id)
    return SuccessResponse(data=result, meta=_meta())


@router.post(
    "/internal/enrollments/{enrollment_id}/cancel",
    response_model=SuccessResponse[ProgressSummaryResponse],
)
async def cancel_progress(
    enrollment_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressSummaryResponse]:
    service = ProgressService(session)
    try:
        result = await service.cancel_progress(enrollment_id=enrollment_id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return SuccessResponse(data=result, meta=_meta())
