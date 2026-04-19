from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_session, require_roles
from app.schemas.analytics import CourseAnalyticsOut, PlatformAnalyticsOut
from app.services.analytics_service import AnalyticsService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["analytics"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/platform", response_model=SuccessResponse[PlatformAnalyticsOut])
async def get_platform_metrics(
    from_date: date = Query(...),
    to_date: date = Query(...),
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PlatformAnalyticsOut]:
    service = AnalyticsService(session)
    result = await service.get_platform_metrics(from_date=from_date, to_date=to_date)
    return SuccessResponse(data=result, meta=_meta())


@router.get("/courses/{course_id}", response_model=SuccessResponse[CourseAnalyticsOut])
async def get_course_metrics(
    course_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CourseAnalyticsOut]:
    service = AnalyticsService(session)
    result = await service.get_course_metrics(
        course_id=course_id,
        requester_id=UUID(current_user["id"]),
        roles=current_user["roles"],
    )
    return SuccessResponse(data=result, meta=_meta())
