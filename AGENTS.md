# EduCorp — Project Guidelines
DO NOT EVER USE THE PATCH TOOL. create and edit like a normal ai.
## Overview

EduCorp is an intelligent course delivery platform: a first-party React web app plus 9 FastAPI microservices communicating via REST, Kafka events, and Temporal workflows.

## Architecture

| Service | Port | Domain | Key Dependencies |
|---------|------|--------|-----------------|
| auth | 8001 | Users, JWT, RBAC | PostgreSQL, Redis |
| course | 8002 | Courses, modules, assets | PostgreSQL, MongoDB, MinIO, Redis |
| enrollment | 8003 | Enrollments, prerequisites, capacity | PostgreSQL, Redis |
| progress | 8004 | Progress tracking, certificates | PostgreSQL, Redis |
| publishing | 8005 | Temporal publishing workflow, versioning | PostgreSQL, Temporal, Qdrant, MinIO, Kafka |
| ai | 8006 | RAG Q&A, instructor tools | PostgreSQL, Redis, Qdrant |
| search | 8007 | Catalog search, semantic retrieval | PostgreSQL, Redis, Qdrant |
| notification | 8008 | Celery workers, in-app + email | PostgreSQL, Redis, RabbitMQ, Kafka |
| analytics | 8009 | Kafka consumers, aggregation | PostgreSQL, Redis, Kafka |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

## Directory Structure

```
apps/web/                      # React 19 + TypeScript + Vite frontend
services/<name>/app/           # FastAPI service code
  main.py                      # App factory + lifespan
  config.py                    # Pydantic Settings
  dependencies.py              # FastAPI Depends()
  models/                      # SQLAlchemy 2.0 async models
  schemas/                     # Pydantic v2 request/response
  api/v1/                      # Route handlers
  services/                    # Business logic
  repositories/                # Data access (repository pattern)
  events/                      # Kafka producers/consumers
shared/educorp_common/         # Shared library (config, DB, middleware, schemas)
infra/                         # Docker, Kafka, Temporal, monitoring configs
scripts/                       # Dev setup, seeding, smoke tests
```

## Tech Stack

- **Language**: Python 3.12+, `from __future__ import annotations`, type hints everywhere
- **Frontend**: React 19, TypeScript, Vite, TanStack Query, React Router
- **Package manager**: `uv`
- **Framework**: FastAPI with app factory pattern + `lifespan`
- **ORM**: SQLAlchemy 2.0 async, schema-per-service, Alembic migrations
- **Databases**: PostgreSQL 16, MongoDB 7 (content), Redis 7 (cache), Qdrant (vectors)
- **Messaging**: Kafka (transactional outbox), RabbitMQ (Celery broker)
- **Workflows**: Temporal
- **AI**: LangChain, LangGraph, NanoGPT (OpenAI-compatible)
- **Infra**: Docker Compose (profiles), Traefik, OpenTelemetry, Prometheus, Grafana, Jaeger
- **Linting**: Ruff (line length 100), Mypy strict

## Build & Run

### Quick Reference (Linux/macOS)

```bash
# Startup options (fastest → fullest)
make up                 # Core infra only (~30s) — postgres, mongodb, redis, qdrant, minio, traefik
make up-messaging       # + Kafka, RabbitMQ, Schema Registry
make up-workflow        # + Temporal
make up-app             # + All 9 application services + frontend
make up-full            # Everything including observability (Prometheus, Grafana, Jaeger)
make start              # Full orchestrated startup with migrations + seeding (recommended first time)

# Development
make logs SERVICE=auth  # Tail specific service logs
make health             # Check all service endpoints
make shell SERVICE=auth # Shell into a service container
make debug-service SERVICE=auth  # Attach debugpy debugger on port 5678
make test SERVICE=auth  # Run tests for a service
make migrate            # Run all Alembic migrations
make seed               # Seed development data

# Maintenance
make down               # Stop all services
make clean              # Remove all containers + volumes
make reset              # Full reset: clean → build → start
```

### Windows (PowerShell)

```powershell
.\make.ps1 up                         # Core infra only
.\make.ps1 up-full                    # Everything
.\make.ps1 start                      # Orchestrated startup
.\make.ps1 logs -Service auth         # Tail logs
.\make.ps1 health                     # Health check
.\make.ps1 debug-service -Service auth # Debug with debugpy
.\make.ps1 down                       # Stop all
```

### Docker Compose Profiles

The stack uses profiles for selective startup to save resources:

| Profile | Services Added |
|---------|---------------|
| *(none)* | postgres, mongodb, redis, qdrant, minio, traefik |
| `messaging` | kafka, zookeeper, schema-registry, rabbitmq, kafka-init |
| `workflow` | temporal, temporal-init, temporal-ui |
| `observability` | prometheus, grafana, jaeger |
| `app` | All 9 services + workers + frontend |
| `full` | Everything |
| `debug` | Same as full (services include debugpy) |

### Debugging

All app services in dev mode include `debugpy`. To debug a single service:

1. `make debug-service SERVICE=auth` — starts auth with debugpy listening on port 5678
2. In VS Code, attach to `localhost:5678` (Python: Remote Attach)
3. Set breakpoints and step through code

Hot-reload is enabled by default — edit code and services restart automatically.

## Key Conventions

- **Async everywhere**: Every I/O operation must use `async/await`
- **Response envelope**: `{"data": ..., "meta": {}}` for success, `{"error": {"code", "message", "details"}}` for errors
- **Never return ORM objects** from endpoints — convert to Pydantic schemas
- **Dependencies via `Depends()`** — never import globals directly
- **Repository pattern**: one repo per aggregate, accepts `AsyncSession`, uses `flush()` not `commit()`
- **Transactional outbox**: never produce to Kafka directly from request handlers
- **Error handling**: custom exceptions inheriting `EduCorpError`, caught by app-level exception handlers
- **Schema isolation**: never query across service schema boundaries — use events or HTTP
- **All tables**: UUID `id`, `created_at`, `updated_at` columns; soft-delete via `deleted_at` where needed
- **Correlation IDs**: every request gets an `X-Correlation-Id` header propagated across services

## Agent Workflow

When working on this project, agents should follow these principles:

### Before Making Changes
1. **Check the phase**: Read `docs/PHASES.md` — only implement features in the current or earlier phases
2. **Check dependencies**: Understand which infra each service needs (see Architecture table)
3. **Read the service's existing code**: Understand `main.py`, `config.py`, `dependencies.py` patterns before adding to a service
4. **Use the shared library**: Check `shared/educorp_common/` for existing utilities before creating new ones

### Service Development Pattern
1. Define Pydantic schemas in `schemas/` (request + response, never return ORM objects)
2. Define SQLAlchemy models in `models/` (inherit from `Base`, `UUIDPrimaryKeyMixin`, `TimestampMixin`)
3. Create repository in `repositories/` (one per aggregate, uses `AsyncSession`)
4. Implement business logic in `services/` (depends on repositories)
5. Wire up routes in `api/v1/` (depends on services via `Depends()`)
6. Create Alembic migration: `make migrate-create SERVICE=<name> MSG="description"`
7. Write tests in `tests/` (use `conftest.py` fixtures: `db_session`, `api_client`, `auth_headers`)

### Testing
```bash
make test-service SERVICE=auth     # Run tests for a service
make test-coverage SERVICE=auth    # With coverage report
make lint                          # Ruff + Mypy
```

## Phase Tracking

Development follows 8 sequential phases (0–7). **Always check [docs/PHASES.md](docs/PHASES.md) before making changes.** Only implement features belonging to the current or earlier phases.

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design, service decomposition
- [DATA_MODELS.md](docs/DATA_MODELS.md) — Complete database schemas
- [API_CONTRACTS.md](docs/API_CONTRACTS.md) — REST API specification
- [AI_SYSTEM.md](docs/AI_SYSTEM.md) — RAG pipeline and LangGraph design
- [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) — Docker Compose, profiles, and infra config
- [SECURITY.md](docs/SECURITY.md) — Security design
- [OBSERVABILITY.md](docs/OBSERVABILITY.md) — Monitoring and tracing
- [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — Testing approach
- [PHASES.md](docs/PHASES.md) — Development phases with milestones
- [FRONTEND.md](docs/FRONTEND.md) — Frontend architecture and patterns
