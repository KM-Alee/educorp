from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_session, require_roles
from app.schemas.progress import (
    CertificateDetailOut,
    CertificateOut,
    EnrollmentProgressOut,
    ModuleCompletionOut,
    ProgressDashboardOut,
)
from app.services.progress_service import ProgressService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["progress"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/enrollments/{enrollment_id}",
    response_model=SuccessResponse[EnrollmentProgressOut],
)
async def get_enrollment_progress(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[EnrollmentProgressOut]:
    service = ProgressService(session)
    data = await service.get_enrollment_progress(
        enrollment_id=enrollment_id,
        user_id=UUID(current_user["id"]),
        roles=current_user["roles"],
    )
    return SuccessResponse(data=data, meta=_meta())


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/complete",
    response_model=SuccessResponse[ModuleCompletionOut],
)
async def complete_module(
    enrollment_id: UUID,
    module_id: UUID,
    current_user: CurrentUser = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ModuleCompletionOut]:
    service = ProgressService(session)
    data = await service.complete_module(
        enrollment_id=enrollment_id,
        module_id=module_id,
        student_id=UUID(current_user["id"]),
        correlation_id=get_correlation_id(),
    )
    await session.commit()
    return SuccessResponse(data=data, meta=_meta())


@router.get(
    "/dashboard",
    response_model=SuccessResponse[ProgressDashboardOut],
)
async def get_dashboard(
    current_user: CurrentUser = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressDashboardOut]:
    service = ProgressService(session)
    data = await service.get_dashboard(UUID(current_user["id"]))
    return SuccessResponse(data=data, meta=_meta())


@router.get(
    "/certificates",
    response_model=SuccessResponse[list[CertificateOut]],
)
async def list_certificates(
    current_user: CurrentUser = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[CertificateOut]]:
    service = ProgressService(session)
    data = await service.list_certificates(UUID(current_user["id"]))
    return SuccessResponse(data=data, meta=_meta())


@router.get(
    "/certificates/{certificate_id}",
    response_model=SuccessResponse[CertificateDetailOut],
    status_code=status.HTTP_200_OK,
)
async def get_certificate(
    certificate_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CertificateDetailOut]:
    service = ProgressService(session)
    data = await service.get_certificate(certificate_id)
    return SuccessResponse(data=data, meta=_meta())
