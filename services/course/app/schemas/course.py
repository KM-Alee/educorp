from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    """Request body for creating a course."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=100)
    difficulty: str | None = Field(default=None, pattern=r"^(beginner|intermediate|advanced)$")
    estimated_duration: str | None = None  # ISO 8601 duration string
    tags: list[str] = Field(default_factory=list)
    max_capacity: int | None = Field(default=None, ge=1)
    prerequisites: list[UUID] = Field(default_factory=list)


class CourseUpdate(BaseModel):
    """Request body for updating a course (partial update)."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=100)
    difficulty: str | None = Field(default=None, pattern=r"^(beginner|intermediate|advanced)$")
    estimated_duration: str | None = None
    tags: list[str] | None = None
    thumbnail_url: str | None = Field(default=None, max_length=500)
    is_public_preview: bool | None = None
    max_capacity: int | None = Field(default=None, ge=1)
    prerequisites: list[UUID] | None = None


class ModuleOut(BaseModel):
    """Module summary within a course response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    asset_count: int = 0


class CourseOut(BaseModel):
    """Full course detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instructor_id: UUID
    title: str
    slug: str
    description: str | None
    short_description: str | None
    category: str | None
    difficulty: str | None
    estimated_duration: str | None
    tags: list[str]
    thumbnail_url: str | None
    is_public_preview: bool
    max_capacity: int | None
    prerequisites: list[str]
    visibility: str
    current_version_id: UUID | None
    modules: list[ModuleOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CourseListItem(BaseModel):
    """Course summary for catalog listings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instructor_id: UUID
    title: str
    slug: str
    short_description: str | None
    category: str | None
    difficulty: str | None
    estimated_duration: str | None
    tags: list[str]
    thumbnail_url: str | None
    visibility: str
    created_at: datetime
