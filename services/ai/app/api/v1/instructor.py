from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_kafka_producer,
    get_mongo_db,
    get_qdrant,
    get_redis,
    get_session,
)
from app.repositories.ai_jobs_repository import AiJobsRepository
from app.repositories.entitlement_repository import EntitlementRepository
from app.schemas.instructor import EnhanceRequest, EnhanceResponse, JobListResponse, JobStatusResponse
from app.services.instructor_service import InstructorService
from educorp_common.errors import EduCorpError, ForbiddenError, NotFoundError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

logger = structlog.get_logger()
router = APIRouter(tags=["ai-instructor"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/instructor/enhance", response_model=SuccessResponse[EnhanceResponse], status_code=202)
async def enhance(
    payload: EnhanceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    mongo_db=Depends(get_mongo_db),
    kafka_producer=Depends(get_kafka_producer),
) -> SuccessResponse[EnhanceResponse]:
    user_id = UUID(current_user["id"])
    service = InstructorService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        mongo_db=mongo_db,
        kafka_producer=kafka_producer,
    )

    job_id = uuid4()
    await service.enqueue_job(
        job_id=job_id,
        job_type=payload.job_type,
        course_id=payload.course_id,
        module_id=payload.module_id if payload.scope == "module" else None,
        scope=payload.scope,
        parameters=payload.parameters,
        requested_by=user_id,
        roles=current_user.get("roles", []),
    )

    return SuccessResponse(
        data=EnhanceResponse(
            job_id=job_id,
            status="QUEUED",
            message="Enhancement job queued. Poll GET /ai/instructor/jobs/{job_id}",
        ),
        meta=_meta(),
    )


@router.get("/instructor/enhance/stream")
async def enhance_stream(
    course_id: UUID = Query(...),
    job_type: str = Query(..., pattern=r"^(summary|objectives|quiz|glossary)$"),
    scope: str = Query(..., pattern=r"^(course|module)$"),
    module_id: UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    mongo_db=Depends(get_mongo_db),
    kafka_producer=Depends(get_kafka_producer),
):
    user_id = UUID(current_user["id"])
    service = InstructorService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        mongo_db=mongo_db,
        kafka_producer=kafka_producer,
    )
    job_id = uuid4()

    async def event_generator():
        try:
            async for event in service.stream_job(
                job_id=job_id,
                job_type=job_type,
                course_id=course_id,
                module_id=module_id if scope == "module" else None,
                scope=scope,
                parameters={},
                requested_by=user_id,
                roles=current_user.get("roles", []),
            ):
                yield event
        except EduCorpError as exc:
            yield {
                "event": "error",
                "data": json.dumps({"code": exc.code, "message": exc.message}),
            }
        except Exception as exc:
            logger.warning("Instructor streaming failed", exc_info=exc)
            yield {
                "event": "error",
                "data": json.dumps({"code": "INTERNAL_ERROR", "message": "Streaming failed"}),
            }

    return EventSourceResponse(event_generator())


@router.get("/instructor/jobs/{job_id}", response_model=SuccessResponse[JobStatusResponse])
async def get_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    mongo_db=Depends(get_mongo_db),
) -> SuccessResponse[JobStatusResponse]:
    repo = AiJobsRepository(mongo_db)
    job = await repo.get_job(str(job_id))
    if not job:
        raise NotFoundError("Job not found")

    await _require_owner(job, current_user, session)

    response = JobStatusResponse(
        job_id=UUID(job["job_id"]),
        job_type=job["job_type"],
        status=job["status"],
        result=job.get("result"),
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at"),
    )
    return SuccessResponse(data=response, meta=_meta())


@router.post("/instructor/jobs/{job_id}/cancel", response_model=SuccessResponse[dict])
async def cancel_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    mongo_db=Depends(get_mongo_db),
    kafka_producer=Depends(get_kafka_producer),
) -> SuccessResponse[dict]:
    repo = AiJobsRepository(mongo_db)
    job = await repo.get_job(str(job_id))
    if not job:
        raise NotFoundError("Job not found")

    await _require_owner(job, current_user, session)

    service = InstructorService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        mongo_db=mongo_db,
        kafka_producer=kafka_producer,
    )
    await service.cancel_job(job_id)

    return SuccessResponse(data={"job_id": str(job_id), "status": "CANCELLED"}, meta=_meta())


@router.get("/instructor/jobs", response_model=SuccessResponse[JobListResponse])
async def list_jobs(
    course_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    mongo_db=Depends(get_mongo_db),
) -> SuccessResponse[JobListResponse]:
    filters: dict[str, object] = {"requested_by": current_user["id"]}
    if course_id:
        filters["course_id"] = str(course_id)
    if status:
        filters["status"] = status
    if job_type:
        filters["job_type"] = job_type

    if course_id:
        await _require_owner({"course_id": str(course_id)}, current_user, session)

    repo = AiJobsRepository(mongo_db)
    items, total = await repo.list_jobs(filters=filters, page=page, page_size=page_size)
    summaries = [
        {
            "job_id": UUID(item["job_id"]),
            "job_type": item["job_type"],
            "status": item["status"],
            "created_at": item.get("created_at"),
        }
        for item in items
    ]

    return SuccessResponse(
        data=JobListResponse(items=summaries, total=total),
        meta=_meta(),
    )


async def _require_owner(job: dict, current_user: CurrentUser, session: AsyncSession) -> None:
    roles = current_user.get("roles", [])
    if "admin" in roles:
        return

    course_id = job.get("course_id")
    if not course_id:
        raise ForbiddenError("Course ownership required")

    repo = EntitlementRepository(session)
    is_owner = await repo.is_course_owner(UUID(current_user["id"]), UUID(course_id))
    if not is_owner:
        raise ForbiddenError("Only the course owner can access this job")
