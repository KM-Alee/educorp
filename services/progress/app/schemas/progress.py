from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProgressDetailModule(BaseModel):
    module_id: UUID
    module_title: str
    is_completed: bool
    progress_percent: float
    completed_at: datetime | None = None


class ProgressCertificateSummary(BaseModel):
    id: UUID
    certificate_number: str
    issued_at: datetime


class ProgressDetailResponse(BaseModel):
    enrollment_id: UUID
    course_id: UUID
    course_title: str
    progress_percent: float
    status: str
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    completed_at: datetime | None = None
    modules: list[ProgressDetailModule]


class ModuleCompletionResponse(BaseModel):
    module_id: UUID
    is_completed: bool
    completed_at: datetime | None = None
    overall_progress_percent: float
    course_completed: bool
    certificate: ProgressCertificateSummary | None = None


class DashboardCourseProgress(BaseModel):
    course_id: UUID
    course_title: str
    progress_percent: float
    status: str
    last_activity_at: datetime | None = None


class DashboardResponse(BaseModel):
    active_courses: int
    completed_courses: int
    total_certificates: int
    courses: list[DashboardCourseProgress]


class CertificateSummary(BaseModel):
    id: UUID
    enrollment_id: UUID
    course_id: UUID
    course_title: str
    certificate_number: str
    issued_at: datetime


class CertificateDetailResponse(BaseModel):
    id: UUID
    enrollment_id: UUID
    student_id: UUID
    course_id: UUID
    course_title: str
    student_name: str
    certificate_number: str
    issued_at: datetime
    metadata: dict