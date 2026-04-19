from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_session
from app.schemas.notification import (
    NotificationOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    NotificationReadAllOut,
)
from app.services.notification_service import NotificationService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["notifications"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/", response_model=SuccessResponse[list[NotificationOut]])
async def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[NotificationOut]]:
    service = NotificationService(session)
    data = await service.list_notifications(
        user_id=UUID(current_user["id"]),
        is_read=is_read,
        limit=limit,
    )
    return SuccessResponse(
        data=[NotificationOut.model_validate(item) for item in data], meta=_meta()
    )


@router.patch("/{notification_id}/read", response_model=SuccessResponse[NotificationOut])
async def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[NotificationOut]:
    service = NotificationService(session)
    result = await service.mark_read(
        notification_id=notification_id,
        user_id=UUID(current_user["id"]),
    )
    await session.commit()
    return SuccessResponse(data=NotificationOut.model_validate(result), meta=_meta())


@router.post("/read-all", response_model=SuccessResponse[NotificationReadAllOut])
async def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[NotificationReadAllOut]:
    service = NotificationService(session)
    updated = await service.mark_all_read(user_id=UUID(current_user["id"]))
    await session.commit()
    return SuccessResponse(data=NotificationReadAllOut(updated_count=updated), meta=_meta())


@router.get("/preferences", response_model=SuccessResponse[NotificationPreferenceOut])
async def get_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[NotificationPreferenceOut]:
    service = NotificationService(session)
    prefs = await service.get_preferences(user_id=UUID(current_user["id"]))
    return SuccessResponse(data=NotificationPreferenceOut.model_validate(prefs), meta=_meta())


@router.patch("/preferences", response_model=SuccessResponse[NotificationPreferenceOut])
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[NotificationPreferenceOut]:
    service = NotificationService(session)
    prefs = await service.update_preferences(
        user_id=UUID(current_user["id"]),
        updates=payload.model_dump(),
    )
    await session.commit()
    return SuccessResponse(data=NotificationPreferenceOut.model_validate(prefs), meta=_meta())
