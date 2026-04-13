# EduCorp

Intelligent course delivery platform — 9 FastAPI microservices communicating via REST, Kafka events, and Temporal workflows.

## Quick Start

```bash
# One-command setup (Linux/macOS)
./scripts/dev-setup.sh

# Or manually:
cp .env.example .env
docker compose up -d
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

## Infrastructure UIs

| Tool | URL | Credentials |
|------|-----|-------------|
| Traefik | http://localhost:8081 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Temporal | http://localhost:8088 | — |
| RabbitMQ | http://localhost:15672 | educorp / educorp_dev |
| MinIO | http://localhost:9001 | educorp / educorp_dev |
| Jaeger | http://localhost:16686 | — |

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
make clean           # Remove containers + volumes
make reset           # Full reset: clean + build + up + migrate + seed
```

## Project Structure

```
educorp/
├── AGENTS.md                    # Project guidelines for AI assistants
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
