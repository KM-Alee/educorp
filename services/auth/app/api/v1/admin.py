from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_session, require_roles
from app.schemas.admin import (
    AdminAuditLogOut,
    AdminDeadLetterOut,
    AdminWorkflowDetailOut,
    AdminWorkflowSummaryOut,
    AdminReviewInstructorApplicationRequest,
    AdminUpdateRolesRequest,
    AdminUpdateStatusRequest,
    AdminUserOut,
)
from app.schemas.auth import InstructorApplicationOut, MessageOut
from app.services.admin_ops_service import AdminOpsService, parse_date_bounds
from app.services.admin_user_service import AdminUserService
from app.services.instructor_application_service import InstructorApplicationService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    PaginatedResponse,
    Pagination,
    ResponseMeta,
    SuccessResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def build_meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def request_context(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


@router.get("/users", response_model=PaginatedResponse[AdminUserOut])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminUserOut]:
    service = AdminUserService(session)
    users, total = await service.list_users(
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
        search=search,
    )
    data: list[AdminUserOut] = []
    for user in users:
        roles = await service.get_role_names(user.id)
        data.append(
            AdminUserOut(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=roles,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )

    total_pages = ceil(total / page_size) if total else 0
    pagination = Pagination(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return PaginatedResponse(data=data, meta=build_meta(), pagination=pagination)


@router.patch("/users/{user_id}/roles", response_model=SuccessResponse[MessageOut])
async def update_roles(
    user_id: UUID,
    payload: AdminUpdateRolesRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[MessageOut]:
    service = AdminUserService(session)
    ip_address, user_agent = request_context(request)
    await service.update_roles(
        user_id=user_id,
        add_roles=payload.add_roles,
        remove_roles=payload.remove_roles,
        admin_id=UUID(current_user["id"]),
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return SuccessResponse(data=MessageOut(message="Roles updated"), meta=build_meta())


@router.patch("/users/{user_id}/status", response_model=SuccessResponse[MessageOut])
async def update_status(
    user_id: UUID,
    payload: AdminUpdateStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[MessageOut]:
    service = AdminUserService(session)
    ip_address, user_agent = request_context(request)
    await service.update_status(
        user_id=user_id,
        is_active=payload.is_active,
        admin_id=UUID(current_user["id"]),
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return SuccessResponse(data=MessageOut(message="Status updated"), meta=build_meta())


@router.get(
    "/instructor-applications",
    response_model=PaginatedResponse[InstructorApplicationOut],
)
async def list_instructor_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[InstructorApplicationOut]:
    service = InstructorApplicationService(session)
    applications, total = await service.list_applications(
        status=status, page=page, page_size=page_size
    )
    data = [
        InstructorApplicationOut(
            id=app.id,
            status=app.status,
            created_at=app.created_at,
        )
        for app in applications
    ]

    total_pages = ceil(total / page_size) if total else 0
    pagination = Pagination(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return PaginatedResponse(data=data, meta=build_meta(), pagination=pagination)


@router.patch(
    "/instructor-applications/{application_id}",
    response_model=SuccessResponse[InstructorApplicationOut],
)
async def review_instructor_application(
    application_id: UUID,
    payload: AdminReviewInstructorApplicationRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[InstructorApplicationOut]:
    service = InstructorApplicationService(session)
    ip_address, user_agent = request_context(request)
    application = await service.review_application(
        application_id=application_id,
        status=payload.status,
        reviewer_id=UUID(current_user["id"]),
        correlation_id=get_correlation_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    data = InstructorApplicationOut(
        id=application.id,
        status=application.status,
        created_at=application.created_at,
    )
    return SuccessResponse(data=data, meta=build_meta())


@router.get("/audit-log", response_model=PaginatedResponse[AdminAuditLogOut])
async def list_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: UUID | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminAuditLogOut]:
    service = AdminOpsService(session)
    start, end = parse_date_bounds(from_date, to_date)
    rows, total = await service.list_audit_log(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        from_date=start,
        to_date=end,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=[AdminAuditLogOut.model_validate(row) for row in rows],
        meta=build_meta(),
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get("/workflows", response_model=PaginatedResponse[AdminWorkflowSummaryOut])
async def list_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: UUID | None = Query(default=None),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminWorkflowSummaryOut]:
    service = AdminOpsService(session)
    payload = await service.list_workflows(
        params={
            "page": str(page),
            "page_size": str(page_size),
            **({"status": status_filter} if status_filter else {}),
            **({"course_id": str(course_id)} if course_id else {}),
        }
    )
    return PaginatedResponse(
        data=[AdminWorkflowSummaryOut.model_validate(item) for item in payload.get("data", [])],
        meta=build_meta(),
        pagination=Pagination.model_validate(payload.get("pagination", {})),
    )


@router.get("/workflows/{workflow_id}", response_model=SuccessResponse[AdminWorkflowDetailOut])
async def get_workflow(
    workflow_id: str,
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AdminWorkflowDetailOut]:
    service = AdminOpsService(session)
    payload = await service.get_workflow(workflow_id)
    return SuccessResponse(
        data=AdminWorkflowDetailOut.model_validate(payload["data"]),
        meta=build_meta(),
    )


@router.post(
    "/workflows/{workflow_id}/retry", response_model=SuccessResponse[AdminWorkflowSummaryOut]
)
async def retry_workflow(
    workflow_id: str,
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AdminWorkflowSummaryOut]:
    service = AdminOpsService(session)
    payload = await service.retry_workflow(workflow_id)
    return SuccessResponse(
        data=AdminWorkflowSummaryOut.model_validate(payload["data"]),
        meta=build_meta(),
    )


@router.get("/dlq", response_model=PaginatedResponse[AdminDeadLetterOut])
async def list_dead_letters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    topic: str | None = Query(default=None),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminDeadLetterOut]:
    service = AdminOpsService(session)
    rows, total = await service.list_dead_letters(topic=topic, page=page, page_size=page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=[AdminDeadLetterOut.model_validate(row) for row in rows],
        meta=build_meta(),
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post("/dlq/{message_id}/replay", response_model=SuccessResponse[AdminDeadLetterOut])
async def replay_dead_letter(
    message_id: UUID,
    source: str = Body(embed=True),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AdminDeadLetterOut]:
    service = AdminOpsService(session)
    payload = await service.replay_dead_letter(source=source, message_id=str(message_id))
    data = dict(payload["data"])
    data["source"] = source
    return SuccessResponse(data=AdminDeadLetterOut.model_validate(data), meta=build_meta())
