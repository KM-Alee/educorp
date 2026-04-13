from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModuleCreate(BaseModel):
    """Request body for creating a module."""

    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    sort_order: int | None = None  # auto-assigned if omitted
    is_required: bool = True


class ModuleUpdate(BaseModel):
    """Request body for updating a module."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    is_required: bool | None = None


class ModuleReorder(BaseModel):
    """Request body for reordering modules."""

    order: list[UUID]


class ModuleDetail(BaseModel):
    """Full module response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    estimated_duration: str | None
    created_at: datetime
    updated_at: datetime
