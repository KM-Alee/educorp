from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CourseEnrollmentModule(BaseModel):
    """Internal module snapshot used by enrollment and progress services."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    sort_order: int
    is_required: bool


class CourseEnrollmentContext(BaseModel):
    """Internal course snapshot used for enrollment and progress coordination."""

    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    title: str
    visibility: str
    current_version_id: UUID | None
    max_capacity: int | None
    prerequisites: list[str]
    modules: list[CourseEnrollmentModule]