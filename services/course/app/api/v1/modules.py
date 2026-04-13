from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_session, require_roles
from app.schemas.module import ModuleCreate, ModuleDetail, ModuleReorder, ModuleUpdate
from app.services.module_service import ModuleService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["modules"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _to_detail(m) -> ModuleDetail:
    return ModuleDetail(
        id=m.id,
        course_id=m.course_id,
        title=m.title,
        description=m.description,
        sort_order=m.sort_order,
        is_required=m.is_required,
        estimated_duration=None,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.post(
    "/{course_id}/modules",
    response_model=SuccessResponse[ModuleDetail],
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: UUID,
    payload: ModuleCreate,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ModuleDetail]:
    svc = ModuleService(session)
    module = await svc.create(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
        title=payload.title,
        description=payload.description,
        sort_order=payload.sort_order,
        is_required=payload.is_required,
    )
    await session.commit()
    return SuccessResponse(data=_to_detail(module), meta=_meta())


@router.get(
    "/{course_id}/modules",
    response_model=SuccessResponse[list[ModuleDetail]],
)
async def list_modules(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[ModuleDetail]]:
    svc = ModuleService(session)
    modules = await svc.list_for_course(course_id)
    return SuccessResponse(data=[_to_detail(m) for m in modules], meta=_meta())


@router.patch(
    "/{course_id}/modules/reorder",
    response_model=SuccessResponse[list[ModuleDetail]],
)
async def reorder_modules(
    course_id: UUID,
    payload: ModuleReorder,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[ModuleDetail]]:
    svc = ModuleService(session)
    modules = await svc.reorder(
        course_id=course_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
        ordered_ids=payload.order,
    )
    await session.commit()
    return SuccessResponse(data=[_to_detail(m) for m in modules], meta=_meta())


@router.patch(
    "/{course_id}/modules/{module_id}",
    response_model=SuccessResponse[ModuleDetail],
)
async def update_module(
    course_id: UUID,
    module_id: UUID,
    payload: ModuleUpdate,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ModuleDetail]:
    svc = ModuleService(session)
    module = await svc.update(
        course_id=course_id,
        module_id=module_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
        title=payload.title,
        description=payload.description,
        is_required=payload.is_required,
    )
    await session.commit()
    return SuccessResponse(data=_to_detail(module), meta=_meta())


@router.delete(
    "/{course_id}/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_module(
    course_id: UUID,
    module_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = ModuleService(session)
    await svc.delete(
        course_id=course_id,
        module_id=module_id,
        caller_id=UUID(current_user["id"]),
        caller_roles=current_user["roles"],
    )
    await session.commit()
