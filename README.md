# EduCorp

Intelligent course delivery platform with a first-party web app and 9 FastAPI microservices communicating via REST, Kafka events, and Temporal workflows.

Phase 7 adds the production-readiness layer: shared tracing and metrics wiring, security headers, readiness dependency metrics, admin ops APIs for workflow/DLQ/audit visibility, provisioned Grafana dashboards, Prometheus alert rules, load-test scaffolding, and an operations smoke script.

## Quick Start

```bash
# One-command setup (Linux/macOS)
./scripts/dev-setup.sh

# Or manually:
cp .env.example .env
docker compose up -d

# Frontend (Phase 2 web app)
cd apps/web
npm install
npm run dev
```

```powershell
# One-command setup (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File .\scripts\dev-setup.ps1
```

## Services

| Service | Port | API Prefix | Domain |
|---------|------|------------|--------|
| auth | 8001 | `/api/v1/auth` | Users, JWT, RBAC |
| course | 8002 | `/api/v1/courses` | Course authoring |
| enrollment | 8003 | `/api/v1/enrollments` | Enrollment management |
| progress | 8004 | `/api/v1/progress` | Progress & certificates |
| publishing | 8005 | `/api/v1/publishing` | Temporal publishing pipeline |
| ai | 8006 | `/api/v1/ai` | RAG Q&A, instructor tools |
| search | 8007 | `/api/v1/search` | Catalog & semantic search |
| notification | 8008 | `/api/v1/notifications` | Email & in-app notifications |
| analytics | 8009 | `/api/v1/analytics` | Event aggregation & reporting |

All services are routed through **Traefik** on port 80.

## Frontend

The first-party learner/admin web app lives in `apps/web` and is developed in parallel with the backend phases.

- Phase 1 scope: registration, login, email verification, password reset, profile, admin user management, instructor application review
- Phase 2 scope: course draft creation, module CRUD and reordering, asset upload/download/delete, draft validation, Mongo-backed draft content editing
- Design direction: warm editorial surfaces, restrained depth, and utilitarian auth flows adapted from the `cursor-inspo.md` brief without copying proprietary assets or adding decorative gradients/glow
- API integration: the web app talks directly to the Traefik-routed APIs under `/api/v1/*`

## Infrastructure UIs

| Tool | URL | Credentials |
|------|-----|-------------|
| Traefik | http://localhost:8081 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Temporal | http://localhost:8088 | — |
| RabbitMQ | http://localhost:15672 | educorp / educorp_dev |
| MinIO | http://localhost:9001 | educorp / educorp_dev |
| Jaeger | http://localhost:16686 | — |

## Phase 7 Operations

Observability and operational surfaces are now provisioned for local verification:

- Prometheus scrapes every service `/metrics` endpoint and loads `infra/monitoring/prometheus/alerts.yml`
- Grafana provisions dashboards from `infra/monitoring/grafana/dashboards/`
- Jaeger receives OTLP traces on `4317`
- Admin ops routes are available under `/api/v1/admin/*` for audit log, workflows, and DLQ inspection

Recommended verification flow:

```bash
make up-full
make seed
make smoke-phase4
make smoke-phase5
make smoke-phase7
```

Load and dependency audit helpers:

```bash
make load-test USERS=20 SPAWN_RATE=4 RUN_TIME=2m
make dep-audit
```

## Development Commands

```bash
make up              # Start all services
make down            # Stop all services
make ps              # Show container status
make logs            # Tail logs (SERVICE=auth for specific)
make build           # Build all service images
make migrate         # Run all Alembic migrations
make test            # Run all tests
make lint            # Run ruff + mypy
make kafka-topics    # Create Kafka topics
make kafka-list      # List Kafka topics
make seed            # Seed development data
make smoke-phase4    # Journey B smoke: enroll -> progress -> certificate
make smoke-phase5    # Journey C smoke: AI ask + instructor job
make smoke-phase7    # Admin ops + observability smoke
make load-test       # Locust load run against local gateway
make dep-audit       # pip-audit for shared + all services
make clean           # Remove containers + volumes
make reset           # Full reset: clean + build + up + migrate + seed

# Frontend workspace
npm --prefix apps/web install
npm --prefix apps/web run dev
npm --prefix apps/web run test
npm --prefix apps/web run build
```

## Project Structure

```
educorp/
├── AGENTS.md                    # Project guidelines for AI assistants
├── apps/
│   └── web/                     # First-party React/Vite frontend
├── docker-compose.yml           # Full stack definition
├── Makefile                     # Developer commands
├── pyproject.toml               # Workspace config (ruff, mypy)
├── .env.example                 # Environment template
├── shared/educorp_common/       # Shared Python library
│   ├── config/                  #   Base settings
│   ├── database/                #   SQLAlchemy engine, base models
│   ├── schemas/                 #   Response envelopes
│   ├── middleware/              #   Correlation ID, logging
│   ├── auth/                    #   JWT dependencies (stub)
│   └── errors.py                #   Exception classes + handlers
├── services/<name>/             # 9 FastAPI services
│   ├── app/
│   │   ├── main.py              #   App factory + lifespan
│   │   ├── config.py            #   Pydantic Settings
│   │   ├── dependencies.py      #   FastAPI Depends()
│   │   ├── api/v1/              #   Route handlers
│   │   ├── models/              #   SQLAlchemy models
│   │   ├── schemas/             #   Pydantic schemas
│   │   ├── services/            #   Business logic
│   │   ├── repositories/        #   Data access
│   │   └── events/              #   Kafka producers/consumers
│   ├── alembic/                 #   Migrations (DB services)
│   └── tests/                   #   Unit + integration tests
├── infra/
│   ├── docker/                  #   Shared Dockerfile
│   ├── postgres/                #   Schema init SQL
│   ├── kafka/                   #   Topic creation script
│   ├── temporal/                #   Namespace setup
│   ├── traefik/                 #   Gateway config
│   └── monitoring/              #   Prometheus, Grafana
├── scripts/                     #   Dev utilities
└── docs/                        #   Architecture & design docs
```

## Documentation

See the [docs/](docs/) directory for detailed design documentation.

- `docs/ARCHITECTURE.md` — service and frontend architecture
- `docs/FRONTEND.md` — web app structure, UI system, and route plan
- `docs/PHASES.md` — backend and frontend delivery phases
- `docs/PHASE3_IMPLEMENTATION_PLAN.md` — concrete implementation sequence for publishing and search
- `docs/OBSERVABILITY.md` — metrics, traces, dashboards, alerts, and runbook guidance
- `docs/SECURITY.md` — auth, RBAC, input validation, rate limiting, and hardening notes


#swagger
http://localhost/api/v1/ai/docs
