from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_session, require_internal_service
from app.repositories.course_search_repository import CourseSearchRepository
from app.schemas.search import CourseSearchItem, SemanticSearchRequest, SemanticSearchResponse
from app.services.keyword_search_service import KeywordSearchService
from app.services.semantic_search_service import SemanticSearchService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.schemas.responses import Pagination, PaginatedResponse, ResponseMeta, SuccessResponse

logger = structlog.get_logger()
router = APIRouter(tags=["search"])


def _meta() -> ResponseMeta:
    return ResponseMeta(
        correlation_id=get_correlation_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/courses", response_model=PaginatedResponse[CourseSearchItem])
async def search_courses(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    tags: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CourseSearchItem]:
    repo = CourseSearchRepository(session)
    svc = KeywordSearchService(repo)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    items, total = await svc.search(
        query=q,
        category=category,
        difficulty=difficulty,
        tags=tag_list,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0

    return PaginatedResponse(
        data=items,
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


@router.post("/semantic", response_model=SuccessResponse[SemanticSearchResponse])
async def semantic_search(
    payload: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[SemanticSearchResponse]:
    repo = CourseSearchRepository(session)
    svc = SemanticSearchService(repo)
    chunks = await svc.search(
        course_id=payload.course_id,
        query=payload.query,
        top_k=payload.top_k,
        module_id=payload.module_id,
    )

    return SuccessResponse(
        data=SemanticSearchResponse(
            chunks=chunks,
            query_embedding_model=settings.embedding_model,
            total_results=len(chunks),
        ),
        meta=_meta(),
    )


@router.post(
    "/internal/activate/{course_id}",
    response_model=SuccessResponse[dict],
    include_in_schema=False,
)
async def internal_activate_course(
    course_id: UUID,
    _: None = Depends(require_internal_service),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[dict]:
    """Internal endpoint called by publishing service on course activation.

    The search service uses cross-service SQL joins so no projection update is
    required — this endpoint exists as an acknowledgment hook for future caching.
    """
    logger.info("Course activation received by search service", course_id=str(course_id))
    return SuccessResponse(data={"acknowledged": True, "course_id": str(course_id)}, meta=_meta())
