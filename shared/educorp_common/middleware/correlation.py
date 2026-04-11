from __future__ import annotations

import contextvars
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)

CORRELATION_ID_HEADER = "X-Correlation-Id"


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_ctx.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates a correlation ID for each request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
        correlation_id_ctx.set(cid)

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = cid
        return response
