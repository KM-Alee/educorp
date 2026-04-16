from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublishManifestAssetIn(BaseModel):
    id: UUID
    title: str
    asset_type: str
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    checksum: str
    sort_order: int


class PublishManifestModuleIn(BaseModel):
    id: UUID
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    estimated_duration: str | None
    assets: list[PublishManifestAssetIn] = Field(default_factory=list)


class PublishVersionRequest(BaseModel):
    course_id: UUID
    instructor_id: UUID
    requested_by: UUID
    title: str
    slug: str
    description: str | None
    short_description: str | None
    category: str | None
    difficulty: str | None
    estimated_duration: str | None
    tags: list[str] = Field(default_factory=list)
    generated_at: datetime
    modules: list[PublishManifestModuleIn] = Field(default_factory=list)


class PublishVersionResponse(BaseModel):
    version_id: UUID
    version_number: int
    status: str
    approval_state: str | None = None
    workflow_id: str | None
    message: str


class PublishingArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_type: str
    object_path: str
    sha256: str
    content_type: str
    size_bytes: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


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
    approval_state: str
    initiated_by: UUID
    workflow_id: str | None
    run_id: str | None
    manifest_hash: str
    preflight_summary_json: dict[str, Any] | None
    error_details: dict[str, Any] | None
    total_chunks: int
    total_assets: int
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    ready_at: datetime | None
    activated_at: datetime | None
    superseded_at: datetime | None
    steps: list[PublishingStepOut] = Field(default_factory=list)
    artifacts: list[PublishingArtifactOut] = Field(default_factory=list)

    @property
    def display_status(self) -> str:
        """Human-readable operator state derived from status + approval fields."""
        if self.status == "SUPERSEDED":
            return "SUPERSEDED"
        if self.status in {"FAILED", "CANCELLED"}:
            return self.status
        if self.status == "REVIEW_REQUIRED":
            if self.approval_state == "APPROVED":
                return "APPROVED"
            return "REVIEW_REQUIRED"
        if self.status == "PUBLISHING":
            return "PUBLISHING"
        if self.status == "READY":
            return "ACTIVATED" if self.activated_at is not None else "READY"
        return self.status
