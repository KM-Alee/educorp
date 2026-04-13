from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Standard response metadata."""

    correlation_id: str | None = None
    timestamp: str | None = None


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)
    correlation_id: str | None = None
    timestamp: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail


class Pagination(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response envelope."""

    data: list[T]
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    pagination: Pagination
