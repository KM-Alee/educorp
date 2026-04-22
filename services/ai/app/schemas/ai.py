from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    course_id: UUID
    question: str = Field(..., max_length=2000)
    module_id: UUID | None = None
    asset_id: UUID | None = None


class Citation(BaseModel):
    chunk_id: str
    module_title: str | None = None
    asset_title: str | None = None
    text_snippet: str
    page_number: int | None = None


class AskResponse(BaseModel):
    query_id: UUID
    answer: str
    citations: list[Citation]
    confidence: str
    course_id: UUID
    version_id: UUID
    response_type: str = "answer"


class ClarifyRequest(BaseModel):
    course_id: UUID
    original_query_id: UUID
    clarification: str = Field(..., max_length=2000)


class ClarifyResponse(BaseModel):
    query_id: UUID
    answer: str
    citations: list[Citation]
    confidence: str
    course_id: UUID
    version_id: UUID
    response_type: str = "answer"


class StreamEvent(BaseModel):
    event: str
    data: str | dict[str, Any]
