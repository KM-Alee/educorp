from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EnrollmentCreate(BaseModel):
    """Request payload for creating an enrollment."""

    course_id: UUID
    idempotency_key: str | None = Field(default=None, max_length=255)


class EnrollmentResponse(BaseModel):
    """Enrollment API response."""

    id: UUID
    student_id: UUID
    course_id: UUID
    status: str
    enrolled_at: datetime
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EnrollmentStatusResponse(BaseModel):
    """Course-specific enrollment status response."""

    is_enrolled: bool
    enrollment_id: UUID | None = None
    status: str | None = None
    progress_percent: float | None = None