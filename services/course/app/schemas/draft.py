from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DraftValidationIssue


class DraftValidationResult(BaseModel):
    """Validation result for a course draft."""

    is_valid: bool
    issues: list[DraftValidationIssue] = Field(default_factory=list)


class DraftContentUpdate(BaseModel):
    """Generic rich draft content persisted in MongoDB."""

    content: dict[str, Any] = Field(default_factory=dict)


class DraftContentDocument(BaseModel):
    """Mongo-backed draft content document returned to clients."""

    course_id: UUID
    content: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None