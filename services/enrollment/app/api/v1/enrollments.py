from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_redis,
    get_session,
    require_internal_or_roles,
    require_roles,
)
from app.schemas.enrollment import EnrollmentCreate, EnrollmentOut, EnrollmentStatusOut
from app.services.course_owner_client import CourseOwnerClient
from app.services.enrollment_service import EnrollmentService
from educorp_common.errors import ForbiddenError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    Pagination,
    PaginatedResponse,
    ResponseMeta,
    SuccessResponse,
)

router = APIRouter(tags=["enrollments"])


def _meta(idempotent_hit: bool | None = None) -> ResponseMeta:
    meta = ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    meta.idempotent_hit = idempotent_hit
    return meta


@router.post(
    "/",
    response_model=SuccessResponse[EnrollmentOut],
    status_code=status.HTTP_201_CREATED,
)
async def enroll(
    payload: EnrollmentCreate,
    response: Response,
    current_user: CurrentUser = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentOut]:
    service = EnrollmentService(session, redis)
    result = await service.enroll(
        student_id=UUID(current_user["id"]),
        course_id=payload.course_id,
        idempotency_key=payload.idempotency_key,
        correlation_id=get_correlation_id(),
    )
    if result.idempotent_hit:
        response.status_code = status.HTTP_200_OK
    await session.commit()
    return SuccessResponse(
        data=EnrollmentOut.model_validate(result.enrollment),
        meta=_meta(idempotent_hit=result.idempotent_hit),
    )


@router.get(
    "/",
    response_model=PaginatedResponse[EnrollmentOut],
)
async def list_enrollments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PaginatedResponse[EnrollmentOut]:
    service = EnrollmentService(session, redis)
    enrollments, total = await service.list_enrollments(
        student_id=UUID(current_user["id"]),
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        data=[EnrollmentOut.model_validate(item) for item in enrollments],
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
    "/admin/all",
    response_model=PaginatedResponse[EnrollmentOut],
)
async def list_all_enrollments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PaginatedResponse[EnrollmentOut]:
    """Admin endpoint to list all enrollments across all students and courses."""
    from app.repositories.enrollment_repository import EnrollmentRepository

    repo = EnrollmentRepository(session)
    enrollments, total = await repo.list_all(
        course_id=course_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        data=[EnrollmentOut.model_validate(item) for item in enrollments],
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
    "/courses/{course_id}/enrollments",
    response_model=PaginatedResponse[EnrollmentOut],
)
async def list_course_enrollments(
    course_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PaginatedResponse[EnrollmentOut]:
    """Instructor/admin endpoint to list all enrollments for a specific course."""
    from app.repositories.enrollment_repository import EnrollmentRepository

    if "admin" not in current_user["roles"]:
        ownership = await CourseOwnerClient().get_course_ownership(course_id=course_id)
        if ownership.get("instructor_id") != current_user["id"]:
            raise ForbiddenError("You do not own this course")

    repo = EnrollmentRepository(session)
    enrollments, total = await repo.list_by_course(
        course_id=course_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        data=[EnrollmentOut.model_validate(item) for item in enrollments],
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
    "/{enrollment_id}",
    response_model=SuccessResponse[EnrollmentOut],
)
async def get_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentOut]:
    service = EnrollmentService(session, redis)
    enrollment = await service.get_enrollment(enrollment_id)
    is_admin = "admin" in current_user["roles"]
    if not is_admin and enrollment.student_id != UUID(current_user["id"]):
        raise ForbiddenError("Access forbidden")
    return SuccessResponse(data=EnrollmentOut.model_validate(enrollment), meta=_meta())


@router.post(
    "/{enrollment_id}/cancel",
    response_model=SuccessResponse[EnrollmentOut],
)
async def cancel_enrollment(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentOut]:
    service = EnrollmentService(session, redis)
    enrollment = await service.get_enrollment(enrollment_id)
    is_admin = "admin" in current_user["roles"]
    if not is_admin and enrollment.student_id != UUID(current_user["id"]):
        raise ForbiddenError("Access forbidden")

    enrollment = await service.cancel_enrollment(
        enrollment=enrollment,
        actor_id=UUID(current_user["id"]),
        correlation_id=get_correlation_id(),
    )
    await session.commit()
    return SuccessResponse(data=EnrollmentOut.model_validate(enrollment), meta=_meta())


@router.get(
    "/courses/{course_id}/enrollment-status",
    response_model=SuccessResponse[EnrollmentStatusOut],
)
async def enrollment_status(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentStatusOut]:
    service = EnrollmentService(session, redis)
    enrollment, progress_percent = await service.get_enrollment_status(
        student_id=UUID(current_user["id"]),
        course_id=course_id,
    )
    if enrollment is None:
        data = EnrollmentStatusOut(is_enrolled=False)
    else:
        is_enrolled = enrollment.status in ("ENROLLED", "COMPLETED")
        data = EnrollmentStatusOut(
            is_enrolled=is_enrolled,
            enrollment_id=enrollment.id,
            status=enrollment.status,
            progress_percent=progress_percent,
        )
    return SuccessResponse(data=data, meta=_meta())


@router.get(
    "/internal/courses/{course_id}/students/{student_id}/enrollment-status",
    response_model=SuccessResponse[EnrollmentStatusOut],
)
async def internal_enrollment_status(
    course_id: UUID,
    student_id: UUID,
    _: CurrentUser | None = Depends(require_internal_or_roles("admin")),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SuccessResponse[EnrollmentStatusOut]:
    service = EnrollmentService(session, redis)
    enrollment, progress_percent = await service.get_enrollment_status(
        student_id=student_id,
        course_id=course_id,
    )
    if enrollment is None:
        data = EnrollmentStatusOut(is_enrolled=False)
    else:
        data = EnrollmentStatusOut(
            is_enrolled=enrollment.status in ("ENROLLED", "COMPLETED"),
            enrollment_id=enrollment.id,
            status=enrollment.status,
            progress_percent=progress_percent,
        )
    return SuccessResponse(data=data, meta=_meta())
