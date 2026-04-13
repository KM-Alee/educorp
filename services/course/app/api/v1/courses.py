from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_session, require_roles
from app.schemas.course import CourseCreate, CourseListItem, CourseOut, CourseUpdate
from app.services.course_service import CourseService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import Pagination, PaginatedResponse, ResponseMeta, SuccessResponse

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
    current_user: CurrentUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CourseListItem]:
    svc = CourseService(session)
    caller_roles = current_user["roles"] if current_user else []
    is_privileged = "instructor" in caller_roles or "admin" in caller_roles
    items, total = await svc.list_courses(
        page=page,
        page_size=page_size,
        category=category,
        difficulty=difficulty,
        search=search,
        visibility=visibility if is_privileged else None,
        instructor_id=instructor_id,
        include_drafts=is_privileged,
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
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseOut]:
    svc = CourseService(session)
    result = await svc.get_course(course_id)
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
