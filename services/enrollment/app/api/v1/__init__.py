from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_redis,
    get_session,
    require_internal_service,
    require_roles,
)
from app.schemas.enrollment import EnrollmentCreate, EnrollmentResponse, EnrollmentStatusResponse
from app.schemas.internal import EnrollmentCompletionRequest
from app.services.enrollment_service import EnrollmentService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import Pagination, PaginatedResponse, ResponseMeta, SuccessResponse

from app.api.v1.enrollments import router as enrollments_router

router = APIRouter()

router.include_router(enrollments_router)


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/enrollments/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/enrollments/health/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    return {"status": "ready"}


@router.post(
    "/enrollments",
    response_model=SuccessResponse[EnrollmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_enrollment(
    payload: EnrollmentCreate,
    current_user: CurrentUser = Depends(require_roles("student", "admin")),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentResponse]:
    service = EnrollmentService(session, redis)
    response, idempotent_hit = await service.create_enrollment(
        current_user=current_user,
        payload=payload,
        correlation_id=get_correlation_id(),
    )
    meta = _meta()
    if idempotent_hit:
        meta = ResponseMeta(
            correlation_id=meta.correlation_id,
            timestamp=meta.timestamp,
        )
    return SuccessResponse(data=response, meta=meta)


@router.get(
    "/enrollments",
    response_model=PaginatedResponse[EnrollmentResponse],
)
async def list_enrollments(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PaginatedResponse[EnrollmentResponse]:
    service = EnrollmentService(session, redis)
    items, total = await service.list_enrollments(
        current_user=current_user,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        data=items,
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


@router.get(
    "/enrollments/{enrollment_id}",
    response_model=SuccessResponse[EnrollmentResponse],
)
async def get_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentResponse]:
    service = EnrollmentService(session, redis)
    result = await service.get_enrollment(current_user=current_user, enrollment_id=enrollment_id)
    return SuccessResponse(data=result, meta=_meta())


@router.post(
    "/enrollments/{enrollment_id}/cancel",
    response_model=SuccessResponse[EnrollmentResponse],
)
async def cancel_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentResponse]:
    service = EnrollmentService(session, redis)
    result = await service.cancel_enrollment(
        current_user=current_user,
        enrollment_id=enrollment_id,
        correlation_id=get_correlation_id(),
    )
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/courses/{course_id}/enrollment-status",
    response_model=SuccessResponse[EnrollmentStatusResponse],
)
async def get_enrollment_status(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentStatusResponse]:
    service = EnrollmentService(session, redis)
    result = await service.get_enrollment_status(current_user=current_user, course_id=course_id)
    return SuccessResponse(data=result, meta=_meta())


@router.post(
    "/internal/enrollments/{enrollment_id}/complete",
    response_model=SuccessResponse[EnrollmentResponse],
)
async def mark_enrollment_completed(
    enrollment_id: UUID,
    payload: EnrollmentCompletionRequest,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentResponse]:
    service = EnrollmentService(session, redis)
    result = await service.mark_completed(
        enrollment_id=enrollment_id,
        completed_at=payload.completed_at,
        correlation_id=get_correlation_id(),
    )
    return SuccessResponse(data=result, meta=_meta())
