from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProgressInitModule(BaseModel):
    id: UUID
    title: str
    sort_order: int
    is_required: bool


class ProgressInitRequest(BaseModel):
    enrollment_id: UUID
    student_id: UUID
    course_id: UUID
    course_title: str
    modules: list[ProgressInitModule]
    enrolled_at: datetime


class ProgressInitResponse(BaseModel):
    enrollment_id: UUID
    initialized: bool
    status: str


class ProgressSummaryResponse(BaseModel):
    enrollment_id: UUID
    progress_percent: float
    status: str