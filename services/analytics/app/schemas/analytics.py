from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class PlatformAnalyticsOut(BaseModel):
    """Platform analytics response."""

    from_date: date
    to_date: date
    total_students: int
    enrollments: int
    completions: int
    ai_usage: int
    published_courses: int


class CourseAnalyticsOut(BaseModel):
    """Per-course analytics response."""

    course_id: UUID
    instructor_id: UUID | None = None
    course_title: str | None = None
    total_enrollments: int
    total_completions: int
    completion_rate: float
    ai_queries: int
    published_at: datetime | None = None
    latest_version_id: UUID | None = None
