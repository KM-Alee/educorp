from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from miniopy_async import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from app.api.v1.versions import router as versions_router
from app.config import settings
from app.dependencies import get_session, require_internal_service
from app.schemas.admin import AdminWorkflowDetailOut, AdminWorkflowSummaryOut
from app.services.qdrant_service import QdrantService
from app.services.version_service import PublishingVersionService
from app.workflows.publish_course import PublishCourseWorkflow
from app.workflows.types import PublishCourseInput
from educorp_common.errors import NotFoundError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import (
    PaginatedResponse,
    Pagination,
    ResponseMeta,
    SuccessResponse,
)
from educorp_common.telemetry import set_dependency_status

router = APIRouter()


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _workflow_summary(version) -> AdminWorkflowSummaryOut:
    return AdminWorkflowSummaryOut(
        version_id=version.id,
        workflow_id=version.workflow_id,
        run_id=version.run_id,
        course_id=version.course_id,
        status=version.status,
        approval_state=version.approval_state,
        error_details=version.error_details,
        created_at=version.created_at,
        processing_started_at=version.processing_started_at,
        processing_completed_at=version.processing_completed_at,
        ready_at=version.ready_at,
        activated_at=version.activated_at,
    )


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Readiness probe — verify required dependencies are reachable."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        temporal = await Client.connect(
            f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        await temporal.service_client.check_health()
        checks["temporal"] = "ok"
    except Exception:
        checks["temporal"] = "error"

    try:
        qdrant = QdrantService()
        qdrant._client.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "error"

    try:
        minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        await minio_client.bucket_exists(settings.minio_bucket)
        checks["minio"] = "ok"
    except Exception:
        checks["minio"] = "error"

    for dependency, value in checks.items():
        set_dependency_status(service="publishing-service", dependency=dependency, ok=value == "ok")

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


@router.get(
    "/internal/admin/workflows",
    response_model=PaginatedResponse[AdminWorkflowSummaryOut],
)
async def list_internal_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: UUID | None = Query(default=None),
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminWorkflowSummaryOut]:
    svc = PublishingVersionService(session)
    versions, total = await svc._versions.list_workflows(
        page=page,
        page_size=page_size,
        status=status_filter,
        course_id=course_id,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(
        data=[_workflow_summary(version) for version in versions],
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
    "/internal/admin/workflows/{workflow_id}",
    response_model=SuccessResponse[AdminWorkflowDetailOut],
)
async def get_internal_workflow(
    workflow_id: str,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AdminWorkflowDetailOut]:
    svc = PublishingVersionService(session)
    version = await svc._versions.get_by_workflow_id(workflow_id)
    if version is None:
        raise NotFoundError("Workflow not found")
    version, steps, artifacts = await svc.get_status(version_id=version.id)
    return SuccessResponse(
        data=AdminWorkflowDetailOut(
            **_workflow_summary(version).model_dump(),
            steps=[
                {
                    "id": step.id,
                    "step_name": step.step_name,
                    "status": step.status,
                    "started_at": step.started_at,
                    "completed_at": step.completed_at,
                    "error_message": step.error_message,
                    "metadata": step.step_metadata or {},
                }
                for step in steps
            ],
            artifacts=[
                {
                    "id": artifact.id,
                    "artifact_type": artifact.artifact_type,
                    "object_path": artifact.object_path,
                    "sha256": artifact.sha256,
                    "content_type": artifact.content_type,
                    "size_bytes": artifact.size_bytes,
                    "metadata": artifact.artifact_metadata or {},
                    "created_at": artifact.created_at,
                }
                for artifact in artifacts
            ],
        ),
        meta=_meta(),
    )


@router.post(
    "/internal/admin/workflows/{workflow_id}/retry",
    response_model=SuccessResponse[AdminWorkflowSummaryOut],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_internal_workflow(
    workflow_id: str,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[AdminWorkflowSummaryOut]:
    version_service = PublishingVersionService(session)
    version = await version_service._versions.get_by_workflow_id(workflow_id)
    if version is None:
        raise NotFoundError("Workflow not found")

    version = await version_service.prepare_retry(version_id=version.id)
    await session.commit()

    temporal = await Client.connect(
        f"{settings.temporal_host}:{settings.temporal_port}",
        namespace=settings.temporal_namespace,
    )
    handle = await temporal.start_workflow(
        PublishCourseWorkflow.run,
        PublishCourseInput(version_id=version.id),
        id=version.workflow_id,
        task_queue=settings.temporal_task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
    version = await version_service.attach_run_id(version_id=version.id, run_id=handle.run_id)
    await session.commit()
    return SuccessResponse(data=_workflow_summary(version), meta=_meta())


router.include_router(versions_router)
