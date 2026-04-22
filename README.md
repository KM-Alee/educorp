# EduCorp

EduCorp is an AI-powered learning platform. Instructors create and publish courses with AI assistance. Students enroll, track their progress, and receive verifiable certificates. Administrators manage users, review applications, and monitor the platform through built-in observability tooling.

The system is composed of nine independent backend services, a React frontend, and a full local development stack orchestrated through Docker Compose.

---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Repository Layout](#repository-layout)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Developer Commands](#developer-commands)
- [Services and Ports](#services-and-ports)
- [Testing](#testing)
- [Database Migrations](#database-migrations)
- [Scripts Reference](#scripts-reference)
- [Default Credentials](#default-credentials)

---

## Architecture

The platform is built around nine FastAPI microservices, each with its own database schema, and a React single-page application. All services are exposed through a Traefik reverse proxy at `http://localhost` under `/api/v1/<service>`.

**Backend services**

| Service | Path prefix | Datastore |
|-------------|----------------------|-----------|
| auth | `/api/v1/auth` | PostgreSQL |
| course | `/api/v1/courses` | PostgreSQL |
| enrollment | `/api/v1/enrollments` | PostgreSQL |
| progress | `/api/v1/progress` | PostgreSQL |
| publishing | `/api/v1/publishing` | PostgreSQL |
| notification | `/api/v1/notifications` | PostgreSQL |
| analytics | `/api/v1/analytics` | PostgreSQL |
| ai | `/api/v1/ai` | MongoDB, Qdrant |
| search | `/api/v1/search` | Qdrant |

**Messaging and workflow**

Course publishing and AI enrichment jobs run as Temporal workflows, triggered through a RabbitMQ event bus. Domain events between services are published and consumed via Kafka.

**Technology choices**

| Layer | Technology |
|-------------|------------------------------------------------------------------|
| Frontend | React 19, TypeScript, Vite, React Query, React Router, Zod |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic |
| AI | OpenAI-compatible embedding and completion APIs, Qdrant |
| Workflow | Temporal |
| Messaging | Kafka, RabbitMQ |
| Storage | PostgreSQL, MongoDB, Redis, MinIO, Qdrant |
| Gateway | Traefik |
| Observability | Prometheus, Grafana, Jaeger |
| Tooling | uv, ruff, mypy, pytest |

---

## Prerequisites

**Required for all workflows**

- [Docker Desktop](https://docs.docker.com/get-docker/) or Docker Engine with Compose v2
- [Python 3.12 or later](https://python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — the Python package manager used across the workspace

**Required for frontend-only work**

- Node.js 20 or later

**Platform-specific**

- Linux/macOS: GNU `make` (usually pre-installed)
- Windows: PowerShell 5.1 or later (PowerShell 7 recommended)

---

## Repository Layout

```text
.
├── apps/
│   └── web/                    React frontend application
├── services/
│   ├── ai/                     AI assistant and enrichment service
│   ├── analytics/              Platform and course analytics
│   ├── auth/                   Authentication and user management
│   ├── course/                 Course and curriculum management
│   ├── enrollment/             Enrollment and access control
│   ├── notification/           In-platform notification delivery
│   ├── progress/               Progress tracking and certificates
│   ├── publishing/             Course publishing pipeline (Temporal)
│   └── search/                 Keyword and semantic search
├── shared/                     Shared Python library (educorp-common)
├── infra/
│   ├── docker/                 Service Dockerfile
│   ├── kafka/                  Topic initialization scripts
│   ├── monitoring/             Prometheus and Grafana configuration
│   ├── postgres/               Database initialization SQL
│   ├── temporal/               Temporal namespace setup
│   └── traefik/                Routing configuration
├── scripts/                    Developer automation scripts
├── tests/
│   └── load/                   Locust load test definitions
├── dummy-course/               Sample PDF assets for publish smoke tests
├── docker-compose.yml          Full local stack definition
├── Makefile                    Developer commands for Linux/macOS
├── make.ps1                    Developer commands for Windows
├── run-app.sh                  Linux/macOS startup entrypoint
└── run-app.ps1                 Windows startup entrypoint
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/KM-Alee/educorp.git
cd educorp
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Start the stack

**Linux or macOS**

```bash
./run-app.sh
```

**Windows**

```powershell
.\run-app.ps1
```

The startup script runs in six phases:

1. Checks that Docker is available and running
2. Copies `.env.example` to `.env` if no `.env` file exists
3. Starts core infrastructure (PostgreSQL, MongoDB, Redis, Qdrant, MinIO, Traefik)
4. Starts messaging services (Kafka, RabbitMQ)
5. Starts the Temporal workflow engine
6. Starts all nine application services, runs migrations, and seeds baseline data

Once complete, a health summary is printed with the status of each service.

### 4. Access the application

Open `http://localhost:5173` in your browser. Sign in with the seeded admin account (see [Default Credentials](#default-credentials)).

---

## Configuration

All runtime configuration is read from environment variables. A fully annotated template is provided at `.env.example`. On first startup the template is copied automatically.

**Variables that must be changed for production**

| Variable | Description |
|----------------------|----------------------------------------------|
| `SECRET_KEY` | JWT signing key |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `MONGO_PASSWORD` | MongoDB password |
| `REDIS_PASSWORD` | Redis password |
| `NANOGPT_API_KEY` | LLM provider API key |
| `OPENAI_API_KEY` | Embedding provider API key |
| `MINIO_SECRET_KEY` | Object storage secret |

**AI provider mode**

The AI service supports two modes, controlled by `AI_PROVIDER_MODE`:

- `fake` — returns deterministic stub responses with no external calls. Use this for local development and CI when API keys are not available.
- `live` — calls the configured LLM and embedding endpoints. Requires valid `LLM_API_KEY` and `EMBEDDING_API_KEY` values.

---

## Developer Commands

Both `Makefile` and `make.ps1` expose the same commands. Run `make help` or `.\make.ps1 help` to see the full list.

### Stack lifecycle

| Action | Linux/macOS | Windows |
|----------------------------------|-----------------------------------|--------------------------------------|
| Start core infrastructure only | `make up` | `.\make.ps1 up` |
| Full orchestrated startup | `make start` | `.\make.ps1 start` |
| Start a specific profile | `make up-messaging` | `.\make.ps1 up-messaging` |
| Stop everything | `make down` | `.\make.ps1 down` |
| Show container status | `make ps` | `.\make.ps1 ps` |
| Check service health | `make health` | `.\make.ps1 health` |
| Rebuild all images | `make build` | `.\make.ps1 build` |
| Rebuild one service | `make rebuild-service SERVICE=ai` | `.\make.ps1 rebuild-service -Service ai` |
| Tail logs (all services) | `make logs` | `.\make.ps1 logs` |
| Tail logs (one service) | `make logs SERVICE=auth` | `.\make.ps1 logs -Service auth` |
| Open shell in container | `make shell SERVICE=auth` | `.\make.ps1 shell -Service auth` |
| Full reset (clean + rebuild) | `make reset` | `.\make.ps1 reset` |

### Docker Compose profiles

| Profile | Services included |
|-----------------|--------------------------------------|
| _(default)_ | Core infrastructure + Traefik |
| `messaging` | + Kafka, RabbitMQ, Schema Registry |
| `workflow` | + Temporal |
| `app` | + All nine application services |
| `observability` | + Prometheus, Grafana, Jaeger |
| `full` | Everything |

### Code quality

```bash
# Lint (ruff + mypy)
make lint

# Auto-format
make fmt

# Dependency vulnerability audit
make dep-audit
```

### Frontend development

```bash
cd apps/web
npm install
npm run dev        # Vite dev server at http://localhost:5173
npm run build      # Production build
npm run lint       # ESLint
npm test           # Vitest
```

---

## Services and Ports

All API traffic in local development flows through Traefik at `http://localhost`. Direct container ports are available for database tooling and administrative UIs.

| Service | URL | Notes |
|-----------------------|-----------------------------------|-------------------------------|
| Frontend (Vite) | http://localhost:5173 | Dev server only |
| API Gateway | http://localhost | Traefik reverse proxy |
| Traefik Dashboard | http://localhost:8081 | Routing and service status |
| Grafana | http://localhost:3000 | Login: `admin` / `admin` |
| Temporal UI | http://localhost:8088 | Workflow visibility |
| RabbitMQ Management | http://localhost:15672 | Login: `educorp` / `educorp_dev` |
| MinIO Console | http://localhost:9001 | Login: `educorp` / `educorp_dev` |
| Jaeger | http://localhost:16686 | Distributed trace explorer |
| Prometheus | http://localhost:9090 | Raw metrics |
| Qdrant | http://localhost:6333 | Vector database REST API |
| Schema Registry | http://localhost:8082 | Kafka schema management |
| PostgreSQL | localhost:15432 | `educorp` / `educorp_dev` |

---

## Testing

### Unit and integration tests

Tests for each service run via `uv` against a lightweight test configuration (SQLite in-memory for database services, mocked external calls for AI).

```bash
# Run tests for a specific service
make test-service SERVICE=auth

# Run tests for all supported services
make test

# Run with coverage
make test-coverage SERVICE=auth
```

Individual service tests can also be run directly:

```bash
uv run --project services/auth pytest services/auth/tests -v --tb=short
```

### Smoke tests

Smoke tests validate end-to-end flows against a running local stack.

```bash
make smoke-phase4    # Enrollment, progress, and certificate flow
make smoke-phase5    # AI service flows
make smoke-phase7    # Admin operations and observability
```

For the full course publish flow using the bundled sample assets:

```bash
./scripts/run_e2e.sh                                   # Linux/macOS
uv run python scripts/phase3_dummy_course_publish.py --token <TOKEN>  # any platform
```

### Load tests

```bash
make load-test
# Defaults: 20 users, spawn rate 4/s, duration 2 minutes
# Override: USERS=50 SPAWN_RATE=10 RUN_TIME=5m make load-test
```

---

## Database Migrations

Migrations are managed per-service with Alembic and run automatically on startup. To manage them manually:

```bash
# Run all pending migrations
make migrate

# Run migrations for one service
make migrate-service SERVICE=course

# Generate a new migration
make migrate-create SERVICE=course MSG="add estimated duration column"
```

---

## Scripts Reference

| Script | Purpose |
|------------------------------------------|------------------------------------------------------|
| `scripts/start-stack.sh` | Orchestrated Linux/macOS stack startup |
| `scripts/start-stack.ps1` | Orchestrated Windows stack startup |
| `scripts/dev-setup.sh` | Full Linux/macOS development bootstrap |
| `scripts/dev-setup.ps1` | Full Windows development bootstrap |
| `scripts/seed_data.py` | Seed demo users and courses through the live API |
| `scripts/get_token.py` | Fetch a local admin JWT token for manual testing |
| `scripts/run_e2e.sh` | Wrapper for the phase 3 end-to-end publish flow |
| `scripts/phase1_auth_smoke.py` | Auth service smoke checks |
| `scripts/phase3_dummy_course_publish.py` | End-to-end dummy-course publish and activate flow |
| `scripts/phase4_smoke.py` | Enrollment, progress, and certificate smoke test |
| `scripts/phase5_smoke.py` | AI assistant and enrichment smoke test |
| `scripts/phase7_ops_smoke.py` | Admin and observability smoke test |
| `scripts/e2e_ai_test.py` | Extended AI pipeline end-to-end test |
| `scripts/test_semantic.py` | Semantic search validation helper |

---

## Default Credentials

These credentials are created during the seed phase and apply to a local development stack only.

| Account | Email | Password | Role |
|-----------|--------------------------|----------------|-----------|
| Admin | admin@educorp.dev | AdminPass123! | Admin |
| Instructor | instructor@educorp.dev | InstructorPass123! | Instructor |
| Student | student@educorp.dev | StudentPass123! | Student |

Do not use these credentials in any environment exposed to a network.