from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

if TYPE_CHECKING:
    from educorp_common.config.base import BaseAppSettings

REQUEST_COUNTER = Counter(
    "educorp_requests_total",
    "Total request count by service.",
    ["service", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "educorp_request_duration_seconds",
    "Request duration in seconds by service.",
    ["service", "method", "path"],
)
DEPENDENCY_STATUS = Gauge(
    "educorp_dependency_up",
    "Dependency health state exposed by services.",
    ["service", "dependency"],
)
DOMAIN_EVENT_COUNTER = Counter(
    "educorp_domain_events_total",
    "Domain events handled by service.",
    ["service", "event_type", "outcome"],
)

_instrumented_fastapi_apps: set[int] = set()
_instrumented_sqlalchemy_engines: set[int] = set()
_tracing_initialized: set[str] = set()


def setup_tracing(settings: BaseAppSettings) -> None:
    """Initialize OpenTelemetry tracing once per service process."""
    if not settings.traces_enabled or settings.service_name in _tracing_initialized:
        return

    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.namespace": "educorp",
            "deployment.environment": settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(provider)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    _tracing_initialized.add(settings.service_name)


def instrument_sqlalchemy(engine: Any) -> None:
    """Instrument SQLAlchemy engines once."""
    engine_id = id(engine)
    if engine_id in _instrumented_sqlalchemy_engines:
        return
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    _instrumented_sqlalchemy_engines.add(engine_id)


def instrument_app(app: Any, settings: BaseAppSettings) -> None:
    """Attach FastAPI tracing and Prometheus metrics."""
    app_id = id(app)
    if app_id in _instrumented_fastapi_apps:
        return

    if settings.traces_enabled:
        FastAPIInstrumentor.instrument_app(app)

    if settings.metrics_enabled:
        # Tests create multiple FastAPI apps in one process; use a per-app registry so
        # middleware metrics do not collide in the global collector registry.
        registry = CollectorRegistry(auto_describe=True)
        Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=False,
            should_instrument_requests_inprogress=False,
            excluded_handlers=[
                "/metrics",
            ],
            registry=registry,
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    _instrumented_fastapi_apps.add(app_id)


def record_request_metric(
    *, service: str, method: str, path: str, status_code: int, duration: float
) -> None:
    REQUEST_COUNTER.labels(
        service=service,
        method=method,
        path=path,
        status=str(status_code),
    ).inc()
    REQUEST_LATENCY.labels(service=service, method=method, path=path).observe(duration)


def set_dependency_status(*, service: str, dependency: str, ok: bool) -> None:
    DEPENDENCY_STATUS.labels(service=service, dependency=dependency).set(1 if ok else 0)


def record_domain_event(*, service: str, event_type: str, outcome: str) -> None:
    DOMAIN_EVENT_COUNTER.labels(
        service=service,
        event_type=event_type,
        outcome=outcome,
    ).inc()
