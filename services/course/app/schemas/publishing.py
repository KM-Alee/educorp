from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PublishManifestAsset(BaseModel):
    id: UUID
    title: str
    asset_type: str
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    checksum: str
    sort_order: int


class PublishManifestModule(BaseModel):
    id: UUID
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    estimated_duration: str | None
    assets: list[PublishManifestAsset] = Field(default_factory=list)


class PublishManifest(BaseModel):
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
    modules: list[PublishManifestModule] = Field(default_factory=list)


class ActivateCourseVersionRequest(BaseModel):
    version_id: UUID


class PublishVersionResponse(BaseModel):
    version_id: UUID
    version_number: int
    status: str
    approval_state: str | None = None
    workflow_id: str | None
    message: str
