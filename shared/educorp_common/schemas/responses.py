from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    data: T
    meta: dict[str, Any] = {}


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    details: list[dict[str, Any]] = []


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail


class PaginatedMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response envelope."""

    data: list[T]
    meta: PaginatedMeta
