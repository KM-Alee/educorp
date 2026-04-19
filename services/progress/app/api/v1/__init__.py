from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_current_user, get_session, require_internal_service, require_roles
from app.schemas.internal import ProgressInitRequest, ProgressInitResponse, ProgressSummaryResponse
from app.schemas.progress import (
    CertificateDetailResponse,
    CertificateSummary,
    DashboardResponse,
    ModuleCompletionResponse,
    ProgressDetailResponse,
)
from app.services.progress_service import ProgressService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

from app.api.v1.progress import router as progress_router

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
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    return {"status": "ready"}


@router.post(
    "/internal/init",
    response_model=SuccessResponse[ProgressInitResponse],
)
async def initialize_progress(
    payload: ProgressInitRequest,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressInitResponse]:
    service = ProgressService(session)
    result = await service.initialize_progress(payload=payload, correlation_id=get_correlation_id())
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


@router.get(
    "/enrollments/{enrollment_id}",
    response_model=SuccessResponse[ProgressDetailResponse],
)
async def get_progress_detail(
    enrollment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProgressDetailResponse]:
    service = ProgressService(session)
    result = await service.get_progress_detail(current_user=current_user, enrollment_id=enrollment_id)
    return SuccessResponse(data=result, meta=_meta())


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/complete",
    response_model=SuccessResponse[ModuleCompletionResponse],
)
async def complete_module(
    enrollment_id: UUID,
    module_id: UUID,
    current_user: CurrentUser = Depends(require_roles("student", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ModuleCompletionResponse]:
    service = ProgressService(session)
    result = await service.complete_module(
        current_user=current_user,
        enrollment_id=enrollment_id,
        module_id=module_id,
        correlation_id=get_correlation_id(),
    )
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/dashboard",
    response_model=SuccessResponse[DashboardResponse],
)
async def get_dashboard(
    current_user: CurrentUser = Depends(require_roles("student", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[DashboardResponse]:
    service = ProgressService(session)
    result = await service.get_dashboard(current_user=current_user)
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/certificates",
    response_model=SuccessResponse[list[CertificateSummary]],
)
async def list_certificates(
    current_user: CurrentUser = Depends(require_roles("student", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[CertificateSummary]]:
    service = ProgressService(session)
    result = await service.list_certificates(current_user=current_user)
    return SuccessResponse(data=result, meta=_meta())


@router.get(
    "/certificates/{certificate_id}",
    response_model=SuccessResponse[CertificateDetailResponse],
)
async def get_certificate_detail(
    certificate_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[CertificateDetailResponse]:
    service = ProgressService(session)
    result = await service.get_certificate_detail(certificate_id=certificate_id)
    return SuccessResponse(data=result, meta=_meta())
