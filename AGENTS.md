# EduCorp — Project Guidelines

## Overview

EduCorp is an intelligent course delivery platform: a first-party React web app plus 9 FastAPI microservices communicating via REST, Kafka events, and Temporal workflows.

## Architecture

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

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

## Directory Structure

```
apps/web/                      # First-party React/Vite frontend
services/<name>/app/          # FastAPI service code
  main.py                     # App factory + lifespan
  config.py                   # Pydantic Settings
  dependencies.py             # FastAPI Depends()
  models/                     # SQLAlchemy 2.0 async models
  schemas/                    # Pydantic v2 request/response
  api/v1/                     # Route handlers
  services/                   # Business logic
  repositories/               # Data access (repository pattern)
  events/                     # Kafka producers/consumers
shared/educorp_common/        # Shared library (config, DB, middleware, schemas)
infra/                        # Docker, Kafka, Temporal, monitoring configs
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
- **Infra**: Docker Compose, Traefik, OpenTelemetry, Prometheus, Grafana, Jaeger
- **Linting**: Ruff (line length 100), Mypy strict

## Build & Test

```bash
make up              # Start all services
make down            # Stop all services
make migrate         # Run all Alembic migrations
make test            # Run all tests
make lint            # Ruff + Mypy
make kafka-list      # List Kafka topics
```

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

## Phase Tracking

Development follows 8 sequential phases (0–7). **Always check [docs/PHASES.md](docs/PHASES.md) before making changes.** Only implement features belonging to the current or earlier phases.

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design, service decomposition
- [DATA_MODELS.md](docs/DATA_MODELS.md) — Complete database schemas
- [API_CONTRACTS.md](docs/API_CONTRACTS.md) — REST API specification
- [AI_SYSTEM.md](docs/AI_SYSTEM.md) — RAG pipeline and LangGraph design
- [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) — Docker Compose and infra config
- [SECURITY.md](docs/SECURITY.md) — Security design
- [OBSERVABILITY.md](docs/OBSERVABILITY.md) — Monitoring and tracing
- [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — Testing approach
- [PHASES.md](docs/PHASES.md) — Development phases with milestones
