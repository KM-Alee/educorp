from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreate(BaseModel):
    """Request body for creating an enrollment."""

    course_id: UUID
    idempotency_key: str | None = Field(default=None, max_length=255)


class EnrollmentOut(BaseModel):
    """Enrollment response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    status: str
    enrolled_at: datetime


class EnrollmentStatusOut(BaseModel):
    """Enrollment status response for a course."""

    is_enrolled: bool
    enrollment_id: UUID | None = None
    status: str | None = None
    progress_percent: float | None = None
