from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from educorp_common.middleware.correlation import CorrelationIdMiddleware
from educorp_common.middleware.security import SecurityHeadersMiddleware
from educorp_common.telemetry import instrument_app, record_request_metric, setup_tracing

if TYPE_CHECKING:
    from fastapi import Request

    from educorp_common.config.base import BaseAppSettings


def configure_http_app(app: Any, settings: BaseAppSettings) -> None:
    """Apply shared middleware and observability to a FastAPI app."""
    setup_tracing(settings)
    app.add_middleware(CorrelationIdMiddleware)
    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)

    @app.middleware("http")
    async def _record_metrics(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started
        if settings.metrics_enabled:
            record_request_metric(
                service=settings.service_name,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
            )
        return response

    instrument_app(app, settings)
