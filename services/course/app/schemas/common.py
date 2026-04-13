from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class DraftValidationIssue(BaseModel):
    """Single validation issue found during draft validation."""

    field: str
    message: str
    severity: str = "error"  # error | warning
