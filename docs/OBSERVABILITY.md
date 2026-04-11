# EduCorp — Observability Design

## 1. Observability Stack

```
┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│  Application  │───▶│ OpenTelemetry│───▶│   Backends   │
│   Services    │    │   SDK/Agent  │    │              │
└───────────────┘    └──────┬───────┘    │ ┌──────────┐ │
                            │            │ │ Jaeger   │ │ ← Traces
                            │            │ └──────────┘ │
                            │            │ ┌──────────┐ │
                            ├───────────▶│ │Prometheus│ │ ← Metrics
                            │            │ └──────────┘ │
                            │            │ ┌──────────┐ │
                            └───────────▶│ │ stdout   │ │ ← Logs (JSON)
                                         │ └──────────┘ │
                                         └──────┬───────┘
                                                │
                                         ┌──────▼───────┐
                                         │   Grafana    │
                                         │  Dashboards  │
                                         └──────────────┘
```

## 2. OpenTelemetry Integration

### 2.1 Shared Telemetry Setup

Every service initializes OpenTelemetry in the same way via the shared library:

```python
# shared/educorp_common/telemetry/setup.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def setup_telemetry(service_name: str, otlp_endpoint: str) -> None:
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": "educorp",
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint),
        export_interval_millis=15000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument libraries
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()


def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(app)
```

### 2.2 Service Initialization

```python
# In each service's main.py
from educorp_common.telemetry import setup_telemetry, instrument_fastapi

app = FastAPI(title="auth-service")

@app.on_event("startup")
async def startup():
    setup_telemetry(
        service_name="auth-service",
        otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    )
    instrument_fastapi(app)
```

## 3. Structured Logging

### 3.1 Log Format

All services emit JSON-structured logs:

```python
# shared/educorp_common/telemetry/logging.py
import structlog
import logging


def setup_logging(service_name: str, log_level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### 3.2 Log Structure

Every log entry contains:

```json
{
  "timestamp": "2026-04-11T12:00:00.123Z",
  "level": "info",
  "service": "enrollment-service",
  "correlation_id": "uuid",
  "user_id": "uuid",
  "message": "Enrollment created",
  "enrollment_id": "uuid",
  "course_id": "uuid",
  "trace_id": "abc123",
  "span_id": "def456",
  "duration_ms": 45
}
```

### 3.3 Correlation ID Middleware

```python
# shared/educorp_common/middleware/correlation.py
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            service=request.app.title,
        )

        # Store in request state for downstream use
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response
```

## 4. Metrics

### 4.1 Standard Metrics (All Services)

Exposed at `/metrics` via `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

# Auto-instrument FastAPI
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Auto-collected:**
- `http_requests_total{method, path, status}` — Request count
- `http_request_duration_seconds{method, path}` — Latency histogram
- `http_requests_in_progress{method, path}` — Concurrent requests

### 4.2 Custom Business Metrics

```python
# Auth service
auth_login_total = Counter("auth_login_total", "Login attempts", ["status"])  # success/failure
auth_registration_total = Counter("auth_registration_total", "Registrations")
auth_token_refresh_total = Counter("auth_token_refresh_total", "Token refreshes")

# Enrollment service
enrollment_created_total = Counter("enrollment_created_total", "Enrollments", ["course_id"])
enrollment_rejected_total = Counter("enrollment_rejected_total", "Rejected enrollments", ["reason"])
enrollment_capacity_current = Gauge("enrollment_capacity_current", "Current enrollment count", ["course_id"])

# Publishing service
publishing_workflow_total = Counter("publishing_workflow_total", "Publishing workflows", ["status"])
publishing_duration_seconds = Histogram(
    "publishing_duration_seconds", "Publishing duration",
    buckets=[30, 60, 120, 300, 600, 1800, 3600]
)
publishing_chunks_total = Counter("publishing_chunks_total", "Chunks created")

# AI service
ai_query_total = Counter("ai_query_total", "AI queries", ["response_type"])  # answer/refusal/error
ai_query_duration_seconds = Histogram(
    "ai_query_duration_seconds", "AI query latency",
    buckets=[0.5, 1, 2, 5, 10, 20, 30]
)
ai_tokens_used_total = Counter("ai_tokens_used_total", "Tokens consumed", ["direction"])  # input/output
ai_cache_hit_total = Counter("ai_cache_hit_total", "AI cache hits")
ai_retrieval_chunks = Histogram("ai_retrieval_chunks", "Chunks retrieved per query", buckets=[0, 1, 3, 5, 10, 15, 20])

# Kafka consumer
kafka_consumer_lag = Gauge("kafka_consumer_lag", "Consumer lag", ["topic", "partition", "group"])
kafka_messages_processed_total = Counter("kafka_messages_processed_total", "Messages processed", ["topic"])
kafka_dlq_messages_total = Counter("kafka_dlq_messages_total", "DLQ messages", ["topic"])

# Notification service
notification_sent_total = Counter("notification_sent_total", "Notifications sent", ["channel", "type"])
notification_failed_total = Counter("notification_failed_total", "Failed notifications", ["channel", "reason"])
```

## 5. Distributed Tracing

### 5.1 Trace Context Propagation

| Communication | Propagation Method |
|--------------|-------------------|
| HTTP (service-to-service) | W3C Trace Context headers (`traceparent`, `tracestate`) |
| Kafka messages | OpenTelemetry Kafka headers |
| Temporal workflows | OpenTelemetry context in workflow headers |
| Redis | Auto-instrumented by OTel Redis instrumentation |

### 5.2 Key Traced Operations

| Operation | Span Name | Attributes |
|-----------|-----------|-----------|
| API request | `HTTP {method} {path}` | user_id, correlation_id, status_code |
| DB query | `SQL {operation} {table}` | db.statement (sanitized), duration |
| Kafka produce | `{topic} send` | topic, partition, message_key |
| Kafka consume | `{topic} process` | topic, partition, offset, consumer_group |
| Qdrant search | `qdrant.search` | collection, course_id, result_count |
| LLM call | `llm.chat_completion` | model, tokens_in, tokens_out, duration |
| Temporal activity | `temporal.activity.{name}` | workflow_id, run_id, attempt |
| Cache read/write | `redis.{command}` | key_pattern, hit/miss |

### 5.3 Trace Sampling

- **Development**: 100% sampling (capture everything)
- **Production**: Tail-based sampling at 10%, always sample errors and slow requests (>2s)

## 6. Grafana Dashboards

### 6.1 Dashboard Inventory

| Dashboard | Audience | Key Panels |
|-----------|----------|-----------|
| **Platform Overview** | Ops/SRE | Total requests/sec, error rate, p50/p95/p99 latency, active services |
| **Service Health** | Ops/SRE | Per-service: request rate, error rate, latency, CPU, memory |
| **Publishing Pipeline** | Ops/Instructor | Workflow count, success/fail rate, duration by step, active workflows |
| **Enrollment** | Ops/Product | Enrollment rate, rejection reasons, capacity utilization, concurrent enrollments |
| **AI Assistant** | Ops/Product | Query rate, response types, latency, token usage, cache hit rate, refusal rate |
| **Kafka Health** | Ops/SRE | Consumer lag, message rate, DLQ depth, partition distribution |
| **Database** | Ops/SRE | Connection pool usage, query latency, transaction rate, disk usage |

### 6.2 Platform Overview Dashboard (JSON)

```json
{
  "title": "EduCorp Platform Overview",
  "panels": [
    {
      "title": "Request Rate (all services)",
      "type": "stat",
      "query": "sum(rate(http_requests_total[5m]))"
    },
    {
      "title": "Error Rate",
      "type": "gauge",
      "query": "sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) * 100"
    },
    {
      "title": "p95 Latency by Service",
      "type": "timeseries",
      "query": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))"
    },
    {
      "title": "AI Query Latency (p95)",
      "type": "stat",
      "query": "histogram_quantile(0.95, sum(rate(ai_query_duration_seconds_bucket[5m])) by (le))"
    },
    {
      "title": "Enrollment Rate",
      "type": "timeseries",
      "query": "sum(rate(enrollment_created_total[5m])) * 60"
    },
    {
      "title": "Publishing Workflows Active",
      "type": "stat",
      "query": "publishing_workflow_total{status='running'}"
    }
  ]
}
```

## 7. Alerting Rules

### 7.1 Prometheus Alert Rules

```yaml
# infra/monitoring/prometheus/alerts.yml
groups:
  - name: educorp-critical
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency above 2s for {{ $labels.service }}"

      - alert: AIProviderDown
        expr: rate(ai_query_total{response_type="error"}[5m]) / rate(ai_query_total[5m]) > 0.2
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "AI error rate above 20% — provider likely down"

      - alert: KafkaConsumerLag
        expr: kafka_consumer_lag > 10000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag above 10k for {{ $labels.topic }}/{{ $labels.group }}"

      - alert: PublishingFailureSpike
        expr: rate(publishing_workflow_total{status="failed"}[15m]) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Publishing failure rate spiking"

      - alert: EnrollmentFailureSpike
        expr: rate(enrollment_rejected_total[5m]) / rate(enrollment_created_total[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Enrollment rejection rate above 30%"

      - alert: DLQDepthHigh
        expr: kafka_dlq_messages_total > 100
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "DLQ depth above 100 for {{ $labels.topic }}"

      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

## 8. Audit Logging

### 8.1 What Gets Audited

| Event | Actor | Stored Fields |
|-------|-------|--------------|
| User created | System | user_id, email (masked) |
| Role changed | Admin | target_user_id, old_roles, new_roles |
| Login success/failure | User | user_id, IP, device, outcome |
| Course created | Instructor | course_id, title |
| Course published | Instructor | course_id, version_id |
| Enrollment created | Student | enrollment_id, course_id |
| Enrollment cancelled | Student/Admin | enrollment_id, reason |
| Course completed | System | enrollment_id, certificate_id |
| Admin override | Admin | action, target, justification |

### 8.2 Audit Log Query API

```
GET /api/v1/admin/audit-log
    ?actor_id=uuid
    &action=ROLE_CHANGED
    &resource_type=user
    &from_date=2026-04-01
    &to_date=2026-04-11
    &page=1
    &page_size=50
```

## 9. Health Check Patterns

### 9.1 Liveness vs Readiness

```python
@app.get("/health/live")
async def liveness():
    """Is the process running? Always 200 if reachable."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Can this service handle requests?"""
    checks = {}
    all_ok = True

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
        all_ok = False

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"
        all_ok = False

    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code,
    )
```

## 10. Runbooks (Quick Reference)

### 10.1 Publishing Failure Investigation

1. Check Temporal UI (`http://localhost:8088`) → filter by workflow type `PublishCourseWorkflow`
2. Check failed workflow → identify failed activity and error
3. Check publishing step table: `SELECT * FROM publishing.publishing_steps WHERE version_id = ?`
4. Check logs: search by `correlation_id` in service logs
5. Common causes: LLM API timeout (retry), invalid asset (fix and re-publish), Qdrant capacity

### 10.2 Kafka Consumer Lag

1. Check Grafana Kafka dashboard → identify lagging consumer group
2. Check DLQ depth for the topic
3. Check consumer service logs for errors
4. If stuck: restart the consumer service
5. If DLQ growing: investigate message content, replay after fix

### 10.3 AI Provider Outage

1. Check AI dashboard → error rate spike
2. Check LLM provider status page
3. Verify with: `curl ${LLM_BASE_URL}/v1/models`
4. Platform continues working — AI features return graceful errors
5. Cached responses still served
