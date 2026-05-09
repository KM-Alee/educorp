from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from educorp_common.middleware.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class EduCorpError(Exception):
    """Base exception for all EduCorp errors."""

    def __init__(
        self,
        code: str = "INTERNAL_ERROR",
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class NotFoundError(EduCorpError):
    """Resource not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "RESOURCE_NOT_FOUND",
    ) -> None:
        super().__init__(code=code, message=message, status_code=404)


class ConflictError(EduCorpError):
    """Resource conflict."""

    def __init__(
        self, message: str = "Resource conflict", code: str = "CONFLICT"
    ) -> None:
        super().__init__(code=code, message=message, status_code=409)


class ForbiddenError(EduCorpError):
    """Access forbidden."""

    def __init__(
        self, message: str = "Access forbidden", code: str = "FORBIDDEN"
    ) -> None:
        super().__init__(code=code, message=message, status_code=403)


class UnauthorizedError(EduCorpError):
    """Authentication required."""

    def __init__(
        self, message: str = "Authentication required", code: str = "UNAUTHORIZED"
    ) -> None:
        super().__init__(code=code, message=message, status_code=401)


class ValidationError(EduCorpError):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code=code, message=message, status_code=422, details=details
        )


class CircuitBreakerOpenError(EduCorpError):
    """Raised when a downstream circuit breaker is open."""

    def __init__(self, message: str = "Upstream service temporarily unavailable") -> None:
        super().__init__(code="UPSTREAM_CIRCUIT_OPEN", message=message, status_code=503)


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for all EduCorp error types."""

    @app.exception_handler(EduCorpError)
    async def educorp_error_handler(
        request: Request, exc: EduCorpError
    ) -> JSONResponse:
        correlation_id = get_correlation_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "correlation_id": correlation_id,
                    "timestamp": timestamp,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = get_correlation_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        details = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                    "correlation_id": correlation_id,
                    "timestamp": timestamp,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        correlation_id = get_correlation_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.exception(
            "Unhandled exception",
            extra={"correlation_id": correlation_id, "path": str(request.url)},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": [],
                    "correlation_id": correlation_id,
                    "timestamp": timestamp,
                }
            },
        )
