from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUpdateRolesRequest(BaseModel):
    add_roles: list[str] = Field(default_factory=list)
    remove_roles: list[str] = Field(default_factory=list)


class AdminUpdateStatusRequest(BaseModel):
    is_active: bool


class AdminReviewInstructorApplicationRequest(BaseModel):
    status: str


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class AdminAuditLogOut(BaseModel):
    id: str
    source: str
    actor_id: str | None = None
    actor_type: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime


class AdminWorkflowSummaryOut(BaseModel):
    version_id: str
    workflow_id: str | None
    run_id: str | None
    course_id: str
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


class AdminDeadLetterOut(BaseModel):
    id: str
    source: str
    topic: str
    partition: int
    offset: int
    event_type: str | None = None
    error_message: str
    retry_count: int
    raw_message: dict[str, Any] = Field(default_factory=dict)
    replayed_at: datetime | None = None
    created_at: datetime
