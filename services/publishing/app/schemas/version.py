from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublishVersionRequest(BaseModel):
    course_id: UUID


class PublishVersionResponse(BaseModel):
    version_id: UUID
    version_number: int
    status: str
    workflow_id: str | None
    message: str


class PublishingStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublishingVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    version_number: int
    status: str
    initiated_by: UUID
    workflow_id: str | None
    run_id: str | None
    error_details: dict[str, Any] | None
    total_chunks: int
    total_assets: int
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    ready_at: datetime | None
    steps: list[PublishingStepOut] = Field(default_factory=list)
