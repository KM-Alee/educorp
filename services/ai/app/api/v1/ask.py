from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_kafka_producer,
    get_qdrant,
    get_redis,
    get_session,
)
from app.schemas.ai import AskRequest, AskResponse, ClarifyRequest, ClarifyResponse
from app.services.qa_graph import QAService
from app.services.qa_streaming import QAStreamingService
from educorp_common.errors import EduCorpError
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import ResponseMeta, SuccessResponse

logger = structlog.get_logger()
router = APIRouter(tags=["ai"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _role_scope(roles: list[str]) -> str:
    if "admin" in roles:
        return "admin"
    if "instructor" in roles:
        return "instructor"
    return "student"


@router.post("/ask", response_model=SuccessResponse[AskResponse])
async def ask(
    payload: AskRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    kafka_producer=Depends(get_kafka_producer),
) -> SuccessResponse[AskResponse]:
    user_id = UUID(current_user["id"])
    service = QAService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        kafka_producer=kafka_producer,
    )
    state = await service.ask(
        course_id=payload.course_id,
        question=payload.question,
        module_id=payload.module_id,
        user_id=user_id,
        role_scope=_role_scope(current_user.get("roles", [])),
    )

    response = AskResponse(
        query_id=state["query_id"],
        answer=state.get("answer", ""),
        citations=state.get("citations", []),
        confidence=state.get("confidence", "low"),
        course_id=payload.course_id,
        version_id=state["version_id"],
        response_type=state.get("response_type", "answer"),
    )
    return SuccessResponse(data=response, meta=_meta())


@router.get("/ask/stream")
async def ask_stream(
    course_id: UUID = Query(...),
    question: str = Query(..., max_length=2000),
    module_id: UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    kafka_producer=Depends(get_kafka_producer),
):
    user_id = UUID(current_user["id"])
    service = QAStreamingService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        kafka_producer=kafka_producer,
    )

    async def event_generator():
        try:
            async for event in service.stream(
                course_id=course_id,
                question=question,
                module_id=module_id,
                user_id=user_id,
                role_scope=_role_scope(current_user.get("roles", [])),
            ):
                yield event
        except EduCorpError as exc:
            yield {
                "event": "error",
                "data": json.dumps({"code": exc.code, "message": exc.message}),
            }
        except Exception as exc:
            logger.warning("Streaming failed", exc_info=exc)
            yield {
                "event": "error",
                "data": json.dumps({"code": "INTERNAL_ERROR", "message": "Streaming failed"}),
            }

    return EventSourceResponse(event_generator())


@router.post("/ask/clarify", response_model=SuccessResponse[ClarifyResponse])
async def ask_clarify(
    payload: ClarifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
    qdrant=Depends(get_qdrant),
    kafka_producer=Depends(get_kafka_producer),
) -> SuccessResponse[ClarifyResponse]:
    user_id = UUID(current_user["id"])
    service = QAService(
        session=session,
        redis=redis,
        qdrant=qdrant,
        kafka_producer=kafka_producer,
    )
    state = await service.continue_clarification(
        course_id=payload.course_id,
        original_query_id=payload.original_query_id,
        clarification=payload.clarification,
        user_id=user_id,
        role_scope=_role_scope(current_user.get("roles", [])),
    )

    response = ClarifyResponse(
        query_id=state["query_id"],
        answer=state.get("answer", ""),
        citations=state.get("citations", []),
        confidence=state.get("confidence", "low"),
        course_id=payload.course_id,
        version_id=state["version_id"],
        response_type=state.get("response_type", "answer"),
    )
    return SuccessResponse(data=response, meta=_meta())
