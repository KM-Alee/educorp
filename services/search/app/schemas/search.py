from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CourseSearchItem(BaseModel):
    course_id: UUID
    title: str
    short_description: str | None
    instructor_name: str | None = None
    category: str | None
    difficulty: str | None
    relevance_score: float
    matched_in: list[str] = Field(default_factory=list)


class SemanticSearchRequest(BaseModel):
    course_id: UUID
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    module_id: UUID | None = None
    version_status: str = "READY"


class SemanticChunkResult(BaseModel):
    chunk_id: str
    course_id: UUID
    version_id: UUID
    text: str
    score: float
    module_id: UUID
    module_title: str | None
    asset_id: UUID
    asset_title: str | None
    page_or_slide_number: int | None = None
    chunk_index: int
    quality_score: float | None = None


class SemanticSearchResponse(BaseModel):
    chunks: list[SemanticChunkResult]
    query_embedding_model: str
    total_results: int
