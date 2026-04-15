from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from app.config import settings
from app.dependencies import CurrentUser, get_session, require_roles
from app.schemas.version import (
    PublishVersionRequest,
    PublishVersionResponse,
    PublishingStepOut,
    PublishingVersionOut,
)
from app.services.version_service import PublishingVersionService
from app.workflows.publish_course import PublishCourseWorkflow
from app.workflows.types import PublishCourseInput
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

router = APIRouter(tags=["publishing"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/versions",
    response_model=SuccessResponse[PublishVersionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_version(
    payload: PublishVersionRequest,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PublishVersionResponse]:
    svc = PublishingVersionService(session)
    version = await svc.create_version(
        course_id=payload.course_id,
        initiated_by=UUID(current_user["id"]),
    )
    await session.commit()
    try:
        temporal = await Client.connect(
            f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        handle = await temporal.start_workflow(
            PublishCourseWorkflow.run,
            PublishCourseInput(course_id=payload.course_id, version_id=version.id),
            id=version.workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        await svc.attach_run_id(version_id=version.id, run_id=handle.run_id)
        await session.commit()
    except Exception as exc:
        await svc.mark_failed(
            version_id=version.id,
            error_details={"message": str(exc)},
        )
        await session.commit()
        raise

    return SuccessResponse(
        data=PublishVersionResponse(
            version_id=version.id,
            version_number=version.version_number,
            status=version.status,
            workflow_id=version.workflow_id,
            message=(
                "Publishing started. Monitor status via GET /publishing/versions/{version_id}"
            ),
        ),
        meta=_meta(),
    )


@router.get(
    "/versions/{version_id}",
    response_model=SuccessResponse[PublishingVersionOut],
)
async def get_version_status(
    version_id: UUID,
    _current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PublishingVersionOut]:
    svc = PublishingVersionService(session)
    version, steps = await svc.get_status(version_id=version_id)

    return SuccessResponse(
        data=PublishingVersionOut(
            id=version.id,
            course_id=version.course_id,
            version_number=version.version_number,
            status=version.status,
            initiated_by=version.initiated_by,
            workflow_id=version.workflow_id,
            run_id=version.run_id,
            error_details=version.error_details,
            total_chunks=version.total_chunks,
            total_assets=version.total_assets,
            processing_started_at=version.processing_started_at,
            processing_completed_at=version.processing_completed_at,
            created_at=version.created_at,
            ready_at=version.ready_at,
            steps=[
                PublishingStepOut(
                    id=step.id,
                    step_name=step.step_name,
                    status=step.status,
                    started_at=step.started_at,
                    completed_at=step.completed_at,
                    error_message=step.error_message,
                    metadata=step.step_metadata or {},
                )
                for step in steps
            ],
        ),
        meta=_meta(),
    )


@router.post(
    "/versions/{version_id}/retry",
    response_model=SuccessResponse[PublishVersionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_version(
    version_id: UUID,
    current_user: CurrentUser = Depends(require_roles("instructor", "admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PublishVersionResponse]:
    svc = PublishingVersionService(session)
    version = await svc.prepare_retry(version_id=version_id)
    await session.commit()

    temporal = await Client.connect(
        f"{settings.temporal_host}:{settings.temporal_port}",
        namespace=settings.temporal_namespace,
    )
    handle = await temporal.start_workflow(
        PublishCourseWorkflow.run,
        PublishCourseInput(course_id=version.course_id, version_id=version.id),
        id=version.workflow_id,
        task_queue=settings.temporal_task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
    await svc.attach_run_id(version_id=version.id, run_id=handle.run_id)
    await session.commit()

    return SuccessResponse(
        data=PublishVersionResponse(
            version_id=version.id,
            version_number=version.version_number,
            status=version.status,
            workflow_id=version.workflow_id,
            message="Publishing retry started",
        ),
        meta=_meta(),
    )


@router.post(
    "/versions/{version_id}/cancel",
    response_model=SuccessResponse[PublishVersionResponse],
)
async def cancel_version(
    version_id: UUID,
    _current_user: CurrentUser = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[PublishVersionResponse]:
    svc = PublishingVersionService(session)
    version, _steps = await svc.get_status(version_id=version_id)

    if version.workflow_id:
        temporal = await Client.connect(
            f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        await temporal.cancel_workflow(version.workflow_id, run_id=version.run_id)

    version = await svc.mark_cancelled(version_id=version_id)
    await session.commit()

    return SuccessResponse(
        data=PublishVersionResponse(
            version_id=version.id,
            version_number=version.version_number,
            status=version.status,
            workflow_id=version.workflow_id,
            message="Publishing cancelled",
        ),
        meta=_meta(),
    )
