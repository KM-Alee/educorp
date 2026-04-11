# EduCorp — Copilot Workspace Instructions

## Project Overview

EduCorp is an intelligent course delivery platform built as a service-oriented Python backend.
9 FastAPI services communicate via REST, Kafka events, and Temporal workflows.
There is **no frontend** — all services expose a REST API routed through Traefik.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | FastAPI (Python 3.12+, async) |
| **Auth** | JWT (access + refresh), Argon2id, RBAC |
| **Databases** | PostgreSQL 16 (system of record), MongoDB 7 (content), Redis 7 (cache), Qdrant (vectors) |
| **Messaging** | Kafka (domain events), RabbitMQ (Celery broker) |
| **Workflows** | Temporal |
| **AI** | LangChain, LangGraph, NanoGPT (OpenAI-compatible) |
| **Streaming** | SSE (server-sent events) |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Jaeger |
| **Infrastructure** | Docker Compose, Traefik |

## Service Architecture

| Service | Port | Domain |
|---------|------|--------|
| auth | 8001 | Users, JWT, RBAC |
| course | 8002 | Courses, modules, assets |
| enrollment | 8003 | Enrollments, prerequisites, capacity |
| progress | 8004 | Progress tracking, certificates |
| publishing | 8005 | Temporal publishing workflow, versioning |
| ai | 8006 | RAG Q&A, instructor tools |
| search | 8007 | Catalog search, semantic retrieval |
| notification | 8008 | Celery workers, in-app + email |
| analytics | 8009 | Kafka consumers, aggregation |

## Directory Structure

```
services/<name>/
├── app/
│   ├── main.py           # FastAPI app factory + lifespan
│   ├── config.py          # Pydantic Settings
│   ├── dependencies.py    # FastAPI dependencies
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas (request/response)
│   ├── api/v1/            # Route handlers
│   ├── services/          # Business logic
│   ├── repositories/      # Data access
│   └── events/            # Kafka producers/consumers
├── alembic/               # Migrations
├── tests/
└── pyproject.toml
```

## Coding Conventions

### General
- Python 3.12+, type hints everywhere, `from __future__ import annotations`
- Use `uv` as package manager
- Ruff for linting + formatting (line length 100)
- Mypy for type checking (strict)
- Always use async/await for I/O

### FastAPI
- App factory pattern with `lifespan` for startup/shutdown
- Use `APIRouter` with tags and prefix per module
- Dependencies via `Depends()` — never import globals directly
- Pydantic v2 schemas for all request/response bodies
- Standard response envelope: `{"data": ..., "meta": {...}}`
- Error responses: `{"error": {"code": "...", "message": "...", "details": [...]}}`
- Separate `schemas/` (API) from `models/` (ORM) — never return ORM objects from endpoints

### Database
- SQLAlchemy 2.0 with async sessions (`AsyncSession`)
- Repository pattern — one repository class per aggregate
- Alembic for migrations; never modify DB directly
- Use the schema-per-service pattern (`auth.users`, `course.courses`, etc.)
- All tables have `id` (UUID), `created_at`, `updated_at` columns
- Soft-delete via `deleted_at` where needed

### Events & Messaging
- Transactional outbox for reliable event publishing
- Events are JSON with envelope: `{event_type, event_id, timestamp, data, metadata}`
- Kafka topics follow naming: `<domain>.lifecycle`, `<domain>.lifecycle.dlq`
- Consumer groups per service: `<service>-consumers`

### Error Handling
- Use custom exception classes inheriting from a base `EduCorpError`
- Register FastAPI exception handlers in the app factory
- Never expose stack traces to clients
- Log exceptions with correlation_id

### Security
- Validate all inputs via Pydantic
- Use parameterized queries (SQLAlchemy ORM handles this)
- File uploads: validate MIME type + magic bytes + size
- Rate limiting via Redis sliding window
- Idempotency keys for state-changing operations

### Testing
- pytest + pytest-asyncio
- Fixtures: `db_session` (with rollback), `api_client` (httpx.AsyncClient), `auth_headers`
- Factory Boy for test data
- Mocks for LLM calls (respx)
- Target >80% coverage per service

## Documentation References

All design documentation is in `docs/`:
- `docs/ARCHITECTURE.md` — System architecture and service decomposition
- `docs/DATA_MODELS.md` — Complete database schemas
- `docs/API_CONTRACTS.md` — REST API specification
- `docs/AI_SYSTEM.md` — RAG pipeline and LangGraph design
- `docs/INFRASTRUCTURE.md` — Docker Compose and infrastructure config
- `docs/SECURITY.md` — Security design
- `docs/OBSERVABILITY.md` — Monitoring and tracing
- `docs/TESTING_STRATEGY.md` — Testing approach
- `docs/PHASES.md` — Development phases with testable milestones

## Phase Tracking

Development follows 8 sequential phases (see `docs/PHASES.md`).
Always check which phase is currently active before making changes.
Only implement features belonging to the current or earlier phases.
