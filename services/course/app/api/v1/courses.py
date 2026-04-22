from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_mongo_db,
    get_optional_user,
    get_session,
    require_internal_service,
    require_roles,
)
from app.schemas.course import CourseCreate, CourseListItem, CourseOut, CourseUpdate
from app.schemas.draft import DraftContentDocument, DraftContentUpdate, DraftValidationResult
from app.schemas.internal import CourseEnrollmentContext, CourseOwnershipOut
from app.schemas.publishing import ActivateCourseVersionRequest, PublishVersionResponse
from app.services.course_service import CourseService
from app.services.draft_content_service import DraftContentService
from app.services.draft_validation_service import DraftValidationService
from app.services.publishing_client import PublishingClient
from educorp_common.errors import ValidationError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    Pagination,
    PaginatedResponse,
    ResponseMeta,
    SuccessResponse,
)

router = APIRouter(tags=["courses"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/",
    response_model=SuccessResponse[CourseOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_course(
    payload: CourseCreate,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOut]:
    svc = CourseService(session)
    result = await svc.create_course(data=payload, instructor_id=UUID(current_user["id"]))
    await session.commit()
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/",
    response_model=PaginatedResponse[CourseListItem],
)
async def list_courses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    visibility: str | None = None,
    instructor_id: UUID | None = None,
    current_user: CurrentUser | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CourseListItem]:
    svc = CourseService(session)
    caller_roles = current_user["roles"] if current_user else []
    is_admin = "admin" in caller_roles
    is_instructor = "instructor" in caller_roles
    is_privileged = is_admin or is_instructor

    if is_admin:
        effective_instructor_id = instructor_id
        effective_visibility = visibility
        include_drafts = True
    elif is_instructor and current_user:
        effective_instructor_id = UUID(current_user["id"])
        effective_visibility = visibility
        include_drafts = True
    else:
        effective_instructor_id = instructor_id
        effective_visibility = None
        include_drafts = False
    items, total = await svc.list_courses(
        page=page,
        page_size=page_size,
        category=category,
        difficulty=difficulty,
        search=search,
        visibility=effective_visibility if is_privileged else None,
        instructor_id=effective_instructor_id,
        include_drafts=include_drafts,
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
    "/{course_id}",
    response_model=SuccessResponse[CourseOut],
)
async def get_course(
    course_id: UUID,
    current_user: CurrentUser | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOut]:
    svc = CourseService(session)
    caller_id = UUID(current_user["id"]) if current_user else None
    caller_roles = current_user["roles"] if current_user else []
    result = await svc.get_course(
        course_id,
        caller_id=caller_id,
        caller_roles=caller_roles,
    )
    return SuccessResponse(data=result, meta=_meta())


@router.patch(
    "/{course_id}",
    response_model=SuccessResponse[CourseOut],
)
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOut]:
    svc = CourseService(session)
    result = await svc.update_course(
        course_id=course_id,
        data=payload,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    await session.commit()
    return SuccessResponse(data=result, meta=_meta())


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_course(
    course_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = CourseService(session)
    await svc.soft_delete_course(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    await session.commit()


@router.post(
    "/{course_id}/validate",
    response_model=SuccessResponse[DraftValidationResult],
)
async def validate_course_draft(
    course_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[DraftValidationResult]:
    svc = DraftValidationService(session)
    issues = await svc.validate(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    return SuccessResponse(
        data=DraftValidationResult(is_valid=not issues, issues=issues),
        meta=_meta(),
    )


@router.post(
    "/{course_id}/publish",
    response_model=SuccessResponse[PublishVersionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def publish_course(
    course_id: UUID,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PublishVersionResponse]:
    svc = CourseService(session)
    caller_id = UUID(current_user["id"])
    await svc.get_course_for_publish(
        course_id=course_id,
        caller_id=caller_id,
        caller_roles=current_user["roles"],
    )

    validation = DraftValidationService(session)
    issues = await validation.validate(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    if issues:
        raise ValidationError(
            "Draft validation failed",
            details=[issue.model_dump() for issue in issues],
        )

    snapshot = await svc.build_publish_snapshot(
        course_id=course_id,
        caller_id=caller_id,
        caller_roles=current_user["roles"],
    )

    client = PublishingClient()
    result = await client.create_version(
        manifest=snapshot,
        auth_header=request.headers.get("Authorization"),
        correlation_id=get_correlation_id(),
    )
    return SuccessResponse(data=result, meta=_meta())


@router.post(
    "/internal/{course_id}/activate-version",
    response_model=SuccessResponse[CourseOut],
)
async def activate_course_version(
    course_id: UUID,
    payload: ActivateCourseVersionRequest,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOut]:
    svc = CourseService(session)
    result = await svc.activate_course_version(
        course_id=course_id,
        version_id=payload.version_id,
    )
    await session.commit()
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/internal/{course_id}/enrollment-context",
    response_model=SuccessResponse[CourseEnrollmentContext],
)
async def get_course_enrollment_context(
    course_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseEnrollmentContext]:
    svc = CourseService(session)
    result = await svc.get_enrollment_context(course_id=course_id)
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/internal/{course_id}/ownership",
    response_model=SuccessResponse[CourseOwnershipOut],
)
async def get_course_ownership(
    course_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOwnershipOut]:
    svc = CourseService(session)
    result = await svc.get_course_ownership(course_id=course_id)
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/{course_id}/draft-content",
    response_model=SuccessResponse[DraftContentDocument],
)
async def get_course_draft_content(
    course_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),  # type: ignore[type-arg]
) -> SuccessResponse[DraftContentDocument]:
    svc = DraftContentService(session, mongo_db)
    result = await svc.get(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    return SuccessResponse(data=result, meta=_meta())


@router.patch(
    "/{course_id}/draft-content",
    response_model=SuccessResponse[DraftContentDocument],
)
async def update_course_draft_content(
    course_id: UUID,
    payload: DraftContentUpdate,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),  # type: ignore[type-arg]
) -> SuccessResponse[DraftContentDocument]:
    svc = DraftContentService(session, mongo_db)
    result = await svc.update(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
        content=payload.content,
    )
    return SuccessResponse(data=result, meta=_meta())
