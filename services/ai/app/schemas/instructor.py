from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class EnhanceRequest(BaseModel):
    course_id: UUID
    job_type: str = Field(..., pattern=r"^(summary|objectives|quiz|glossary)$")
    scope: str = Field(..., pattern=r"^(course|module)$")
    module_id: UUID | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_module_scope(self) -> "EnhanceRequest":
        if self.scope == "module" and self.module_id is None:
            raise ValueError("module_id is required when scope=module")
        return self


class EnhanceResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    input: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: dict[str, Any] | None = None


class JobSummary(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    input: dict[str, Any] | None = None
    created_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobSummary]
    total: int
