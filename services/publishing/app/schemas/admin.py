from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdminWorkflowSummaryOut(BaseModel):
    version_id: UUID
    workflow_id: str | None
    run_id: str | None
    course_id: UUID
    status: str
    approval_state: str | None = None
    error_details: dict[str, Any] | None = None
    created_at: datetime
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    ready_at: datetime | None = None
    activated_at: datetime | None = None


class AdminWorkflowDetailOut(AdminWorkflowSummaryOut):
    steps: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
