from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EnhanceRequest(BaseModel):
    course_id: UUID
    job_type: str = Field(..., pattern=r"^(summary|objectives|quiz|glossary)$")
    scope: str = Field(..., pattern=r"^(course|module)$")
    module_id: UUID | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class EnhanceResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    result: dict[str, Any] | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class JobSummary(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    created_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobSummary]
    total: int
