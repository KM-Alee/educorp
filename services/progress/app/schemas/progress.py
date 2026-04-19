from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModuleProgressOut(BaseModel):
    """Module progress entry."""

    module_id: UUID
    module_title: str
    is_completed: bool
    progress_percent: float
    completed_at: datetime | None = None


class EnrollmentProgressOut(BaseModel):
    """Enrollment progress details."""

    enrollment_id: UUID
    course_id: UUID
    progress_percent: float
    status: str
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    modules: list[ModuleProgressOut]


class CertificateOut(BaseModel):
    """Certificate summary."""

    id: UUID
    course_id: UUID
    course_title: str
    certificate_number: str
    issued_at: datetime


class CertificateDetailOut(BaseModel):
    """Certificate detail response."""

    id: UUID
    enrollment_id: UUID
    student_id: UUID
    course_id: UUID
    course_title: str
    student_name: str
    certificate_number: str
    issued_at: datetime
    metadata: dict


class ModuleCompletionCertificate(BaseModel):
    """Certificate info returned on completion."""

    id: UUID
    certificate_number: str
    issued_at: datetime


class ModuleCompletionOut(BaseModel):
    """Module completion response."""

    module_id: UUID
    is_completed: bool
    completed_at: datetime | None = None
    overall_progress_percent: float
    course_completed: bool
    certificate: ModuleCompletionCertificate | None = None


class DashboardCourseOut(BaseModel):
    """Progress summary for a course."""

    course_id: UUID
    course_title: str
    progress_percent: float
    status: str
    last_activity_at: datetime | None = None


class ProgressDashboardOut(BaseModel):
    """Progress dashboard response."""

    active_courses: int
    completed_courses: int
    total_certificates: int
    courses: list[DashboardCourseOut]
