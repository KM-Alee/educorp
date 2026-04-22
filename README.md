# EduCorp

EduCorp is a multi-service learning platform with a React frontend, FastAPI backend services, Docker-based local infrastructure, and developer automation for setup, seeding, smoke tests, and service operations.

This repository is structured to run locally with Docker Compose and `uv`. The supported developer entrypoints are the root `Makefile` and `make.ps1`, plus the platform-specific startup wrappers in the repo root and `scripts/`.

## Stack

- Frontend: React 19, TypeScript, Vite, React Query, React Router
- Backend: FastAPI services, SQLAlchemy, Alembic, Pydantic
- Infra: Docker Compose, PostgreSQL, MongoDB, Redis, Qdrant, MinIO, Kafka, RabbitMQ, Temporal, Traefik, Grafana, Prometheus, Jaeger
- Python tooling: `uv`, `pytest`, `ruff`, `mypy`

## Repository Layout

```text
apps/web/              Frontend application
services/              Backend microservices
shared/                Shared Python package
scripts/               Setup, startup, seed, and smoke-test helpers
infra/                 Container and observability configuration
dummy-course/          Sample course assets for publish flows
tests/                 Load and integration-style test assets
docker-compose.yml     Local stack definition
Makefile               Main developer commands for Unix-like shells
make.ps1               Main developer commands for Windows PowerShell
run-app.sh             Linux/macOS startup wrapper
run-app.ps1            Windows startup wrapper
```

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Python 3.12+
- `uv` installed and available on `PATH`
- Node.js 20+ for frontend-only work

Optional:

- GNU `make` on Linux/macOS
- PowerShell 7+ or Windows PowerShell on Windows

## Quick Start

### Windows

```powershell
uv sync
.\run-app.ps1
```

Or use the command wrapper directly:

```powershell
.\make.ps1 start
```

### Linux or macOS

```bash
uv sync
./run-app.sh
```

Or use `make` directly:

```bash
make start
```

The orchestrated startup scripts will:

1. Ensure `.env` exists
2. Start infrastructure in dependency order
3. Start messaging and workflow services
4. Start application services
5. Run database migrations
6. Seed baseline data
7. Run health checks

## Main Developer Commands

### Cross-platform startup and operations

Linux/macOS:

```bash
make help
make up
make start
make health
make logs SERVICE=auth
make down
```

Windows:

```powershell
.\make.ps1 help
.\make.ps1 up
.\make.ps1 start
.\make.ps1 health
.\make.ps1 logs -Service auth
.\make.ps1 down
```

### Python quality checks

```bash
uv run --group dev ruff check .
uv run --group dev mypy .
uv run pytest
```

### Frontend development

```bash
cd apps/web
npm install
npm run dev
```

## Supported Scripts

The repo keeps only the scripts that are current and useful for local development.

### Primary entrypoints

- `run-app.sh`: main Linux/macOS startup wrapper
- `run-app.ps1`: main Windows startup wrapper
- `scripts/start-stack.sh`: orchestrated Linux/macOS stack startup
- `scripts/start-stack.ps1`: orchestrated Windows stack startup
- `scripts/dev-setup.sh`: full Linux/macOS development bootstrap
- `scripts/dev-setup.ps1`: full Windows development bootstrap

### Seed and smoke-test helpers

- `scripts/seed_data.py`: seed demo users and courses through the live API
- `scripts/phase1_auth_smoke.py`: auth smoke checks
- `scripts/phase3_dummy_course_publish.py`: end-to-end dummy-course publish flow
- `scripts/phase4_smoke.py`: enrollment, progress, and certificate flow
- `scripts/phase5_smoke.py`: AI flow smoke tests
- `scripts/phase7_ops_smoke.py`: admin and observability smoke tests
- `scripts/e2e_ai_test.py`: AI end-to-end helper
- `scripts/test_semantic.py`: semantic search helper
- `scripts/get_token.py`: quick helper for a local admin token
- `scripts/run_e2e.sh`: convenience wrapper around the phase 3 publish flow

## Useful URLs After Startup

- Frontend: http://localhost:5173
- Gateway: http://localhost
- Traefik dashboard: http://localhost:8081
- Grafana: http://localhost:3000
- Temporal UI: http://localhost:8088
- RabbitMQ management: http://localhost:15672
- MinIO console: http://localhost:9001
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Qdrant: http://localhost:6333
- Schema Registry: http://localhost:8082

## Common Workflows

### Re-seed development data

```bash
uv run python scripts/seed_data.py
```

### Run a service test suite

```bash
uv run --project services/auth pytest services/auth/tests -v --tb=short
```

### Run the dummy-course publish flow

```bash
uv run python scripts/get_token.py
uv run python scripts/phase3_dummy_course_publish.py --token <TOKEN>
```

Or on Linux/macOS, use the wrapper:

```bash
./scripts/run_e2e.sh
```

## Notes

- This repository is intended for local development and service integration work.
- Docker is the source of truth for infrastructure and service orchestration.
- `uv` is the supported Python workflow in this repo.
- The root README is the canonical public-facing setup document for the repository.