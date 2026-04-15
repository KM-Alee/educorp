# EduCorp — Infrastructure Guide

## 1. Docker Compose Stack

The entire development environment runs via Docker Compose. All services, databases, message brokers, and monitoring tools are containerized.

### 1.1 Infrastructure Services

| Service | Image | Ports (host) | Purpose |
|---------|-------|-------------|---------|
| PostgreSQL | `postgres:16-alpine` | 15432 | Primary database |
| MongoDB | `mongo:7` | 27017 | Content store |
| Redis | `redis:7-alpine` | 6379 | Cache, rate limiting |
| Qdrant | `qdrant/qdrant:v1.8.0` | 6333, 6334 | Vector search |
| MinIO | `minio/minio:latest` | 9000, 9001 | Object storage (S3-compatible) |
| Kafka | `confluentinc/cp-kafka:7.6.0` | 9092, 29092 | Event streaming |
| ZooKeeper | `confluentinc/cp-zookeeper:7.6.0` | 2181 | Kafka coordination |
| Schema Registry | `confluentinc/cp-schema-registry:7.6.0` | 8082 | Event schema management |
| RabbitMQ | `rabbitmq:3.13-management-alpine` | 5672, 15672 | Celery broker |
| Temporal | `temporalio/auto-setup:1.24` | 7233 | Workflow engine |
| Temporal UI | `temporalio/ui:2.26` | 8088 | Workflow dashboard |
| Prometheus | `prom/prometheus:v2.51.0` | 9090 | Metrics collection |
| Grafana | `grafana/grafana:10.4.0` | 3000 | Dashboards |
| Jaeger | `jaegertracing/all-in-one:1.55` | 16686, 4317, 4318 | Distributed tracing |
| Traefik | `traefik:v3.0` | 80, 8081 | API gateway/reverse proxy |

### 1.2 Application Services

| Service | Build Context | Internal Port | Health Endpoint |
|---------|--------------|---------------|-----------------|
| auth-service | `./services/auth` | 8000 | `/health/ready` |
| course-service | `./services/course` | 8000 | `/health/ready` |
| enrollment-service | `./services/enrollment` | 8000 | `/health/ready` |
| progress-service | `./services/progress` | 8000 | `/health/ready` |
| publishing-service | `./services/publishing` | 8000 | `/health/ready` |
| publishing-worker | `./services/publishing` | — | Temporal heartbeat |
| ai-service | `./services/ai` | 8000 | `/health/ready` |
| search-service | `./services/search` | 8000 | `/health/ready` |
| notification-service | `./services/notification` | 8000 | `/health/ready` |
| notification-worker | `./services/notification` | — | Celery inspect |
| analytics-service | `./services/analytics` | 8000 | `/health/ready` |

## 2. Docker Compose Configuration

### 2.1 Profiles

The stack uses **Docker Compose profiles** for selective startup to save resources:

| Profile | Services Added | Use When |
|---------|---------------|----------|
| *(none)* | postgres, mongodb, redis, qdrant, minio, traefik | Backend dev against raw DBs |
| `messaging` | + kafka, zookeeper, schema-registry, rabbitmq, kafka-init | Working on events/messaging |
| `workflow` | + temporal, temporal-init, temporal-ui | Working on publishing workflows |
| `observability` | + prometheus, grafana, jaeger | Debugging performance/tracing |
| `app` | + all 9 services + workers + frontend | Full app development |
| `full` | Everything above combined | Integration testing |
| `debug` | Same as full (services include debugpy) | Remote debugging sessions |

```bash
docker compose --profile messaging --profile app up -d   # Custom combination
make up-app                                               # All services + infra
make up-full                                              # Everything
```

### 2.2 Resource Limits

All containers have resource limits defined via YAML anchors:

| Tier | Memory Limit | CPU Limit | Used By |
|------|-------------|-----------|---------|
| `x-resource-small` | 256 MB | 0.5 | Redis, Qdrant, ZooKeeper, Schema Registry, MinIO, Traefik |
| `x-resource-medium` | 512 MB | 1.0 | App services, workers, RabbitMQ, Jaeger, Grafana |
| `x-resource-large` | 1 GB | 2.0 | PostgreSQL, MongoDB, Kafka, Temporal, Prometheus |

### 2.3 `docker-compose.yml` structure

```yaml
x-service-defaults: &service-defaults
  restart: unless-stopped
  networks:
    - educorp
  env_file:
    - .env

x-python-service: &python-service
  <<: *service-defaults
  build:
    context: .
    dockerfile: infra/docker/Dockerfile.service
    target: dev
  volumes:
    - ./shared:/app/shared:ro

services:
  # ─── Infrastructure ────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    <<: *service-defaults
    ports:
      - "${POSTGRES_HOST_PORT:-15432}:5432"
    environment:
      POSTGRES_USER: educorp
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-educorp_dev}
      POSTGRES_DB: educorp
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U educorp"]
      interval: 5s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:7
    <<: *service-defaults
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: educorp
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-educorp_dev}
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    <<: *service-defaults
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD:-educorp_dev} --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-educorp_dev}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.8.0
    <<: *service-defaults
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "grep -q ':18BD ' /proc/net/tcp /proc/net/tcp6"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    <<: *service-defaults
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-educorp}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-educorp_dev}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ─── Messaging ─────────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    <<: *service-defaults
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    <<: *service-defaults
    ports:
      - "9092:9092"
      - "29092:29092"
    depends_on:
      zookeeper:
        condition: service_started
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - kafka_data:/var/lib/kafka/data
    healthcheck:
      test: ["CMD-SHELL", "kafka-topics --bootstrap-server localhost:29092 --list"]
      interval: 15s
      timeout: 10s
      retries: 10

  schema-registry:
    image: confluentinc/cp-schema-registry:7.6.0
    <<: *service-defaults
    ports:
      - "8082:8081"
    depends_on:
      kafka:
        condition: service_healthy
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:29092

  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    <<: *service-defaults
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: educorp
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-educorp_dev}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ─── Workflow Engine ───────────────────────────────────
  temporal:
    image: temporalio/auto-setup:1.24.2
    <<: *service-defaults
    ports:
      - "7233:7233"
    environment:
      - DB=postgres12
      - DB_PORT=5432
      - POSTGRES_USER=educorp
      - POSTGRES_PWD=${POSTGRES_PASSWORD:-educorp_dev}
      - POSTGRES_SEEDS=postgres
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "grep -q ':1C41 ' /proc/net/tcp /proc/net/tcp6"]
      interval: 15s
      timeout: 10s
      retries: 10

  temporal-ui:
    image: temporalio/ui:2.26.2
    <<: *service-defaults
    ports:
      - "8088:8080"
    environment:
      TEMPORAL_ADDRESS: temporal:7233
    depends_on:
      temporal:
        condition: service_healthy

  # ─── Observability ─────────────────────────────────────
  prometheus:
    image: prom/prometheus:v2.51.0
    <<: *service-defaults
    ports:
      - "9090:9090"
    volumes:
      - ./infra/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:10.4.0
    <<: *service-defaults
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - ./infra/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./infra/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

  jaeger:
    image: jaegertracing/all-in-one:1.55
    <<: *service-defaults
    ports:
      - "16686:16686"
      - "4317:4317"
      - "4318:4318"
    environment:
      COLLECTOR_OTLP_ENABLED: "true"

  # ─── API Gateway ───────────────────────────────────────
  traefik:
    image: traefik:v3.0
    <<: *service-defaults
    ports:
      - "80:80"
      - "8081:8080"
    volumes:
      - ./infra/traefik/traefik.yml:/etc/traefik/traefik.yml:ro
      - ./infra/traefik/dynamic:/etc/traefik/dynamic:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro

volumes:
  postgres_data:
  mongo_data:
  redis_data:
  qdrant_data:
  minio_data:
  zookeeper_data:
  kafka_data:
  rabbitmq_data:
  prometheus_data:
  grafana_data:

networks:
  educorp:
    driver: bridge
```

## 3. Service Dockerfile

### 3.1 Base Service Dockerfile

The Dockerfile uses a **multi-stage build** with separate `runtime` and `dev` targets:

```dockerfile
# infra/docker/Dockerfile.service

# ── Base: minimal runtime image ──────────────────
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*

# ── Builder: compile/install dependencies ────────
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Shared library first (rarely changes → cached)
COPY shared/ /app/shared/
RUN --mount=type=cache,target=/root/.cache/uv \
    cd /app/shared && uv pip install --system -e .

# Service deps (changes only when pyproject.toml changes)
ARG SERVICE_DIR
COPY ${SERVICE_DIR}/pyproject.toml ${SERVICE_DIR}/uv.lock* /app/service/
RUN --mount=type=cache,target=/root/.cache/uv \
    cd /app/service && uv pip install --system -e .
COPY ${SERVICE_DIR}/ /app/service/

# ── Runtime: production-like ─────────────────────
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
WORKDIR /app/service
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health/ready"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# ── Dev: adds debugpy + watchfiles for hot reload ─
FROM runtime AS dev
USER root
RUN pip install --no-cache-dir debugpy watchfiles
USER appuser
EXPOSE 5678
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Key design decisions:**
- **BuildKit cache mounts** (`--mount=type=cache`) reuse the uv/pip cache across builds
- **`dev` target** includes `debugpy` and `watchfiles` for hot-reload and remote debugging
- **`runtime` target** is production-like: no dev tools, non-root user, built-in `HEALTHCHECK`
- Docker Compose uses `target: dev` for all app services during development

## 4. Database Initialization

### 4.1 PostgreSQL Init Script

```sql
-- infra/postgres/init.sql
-- Creates schemas for all services

-- Create separate schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS course;
CREATE SCHEMA IF NOT EXISTS enrollment;
CREATE SCHEMA IF NOT EXISTS progress;
CREATE SCHEMA IF NOT EXISTS publishing;
CREATE SCHEMA IF NOT EXISTS notification;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Trigram similarity for text search
-- CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector (optional fallback)
```

## 5. Kafka Topic Setup

```bash
#!/usr/bin/env bash
# infra/kafka/topics.sh
# Create Kafka topics with proper configuration

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:29092}"

topics=(
    "user.lifecycle:6:1"
    "course.lifecycle:12:1"
    "enrollment.lifecycle:12:1"
    "progress.lifecycle:12:1"
    "ai.usage:6:1"
    "notification.requests:6:1"
    # Dead letter queues
    "user.lifecycle.dlq:3:1"
    "course.lifecycle.dlq:3:1"
    "enrollment.lifecycle.dlq:3:1"
    "progress.lifecycle.dlq:3:1"
    "ai.usage.dlq:3:1"
    "notification.requests.dlq:3:1"
)

for topic_config in "${topics[@]}"; do
    IFS=':' read -r topic partitions replication <<< "$topic_config"
    kafka-topics --create \
        --bootstrap-server "$BOOTSTRAP_SERVER" \
        --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor "$replication" \
        --if-not-exists
    echo "Created topic: $topic (partitions=$partitions, replication=$replication)"
done
```

## 6. Traefik Configuration

### 6.1 Static Config

```yaml
# infra/traefik/traefik.yml
api:
  dashboard: true
  insecure: true  # Dev only — disable in production

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true

log:
  level: INFO

accessLog: {}

metrics:
  prometheus:
    addServicesLabels: true
```

### 6.2 Dynamic Routing

```yaml
# infra/traefik/dynamic/services.yml
http:
  routers:
    auth:
      rule: "PathPrefix(`/api/v1/auth`) || PathPrefix(`/api/v1/admin`)"
      service: auth-service
      entryPoints:
        - web
      middlewares:
        - cors

    courses:
      rule: "PathPrefix(`/api/v1/courses`)"
      service: course-service
      entryPoints:
        - web
      middlewares:
        - cors

    enrollments:
      rule: "PathPrefix(`/api/v1/enrollments`)"
      service: enrollment-service
      entryPoints:
        - web
      middlewares:
        - cors

    progress:
      rule: "PathPrefix(`/api/v1/progress`)"
      service: progress-service
      entryPoints:
        - web
      middlewares:
        - cors

    publishing:
      rule: "PathPrefix(`/api/v1/publishing`)"
      service: publishing-service
      entryPoints:
        - web
      middlewares:
        - cors

    ai:
      rule: "PathPrefix(`/api/v1/ai`)"
      service: ai-service
      entryPoints:
        - web
      middlewares:
        - cors

    search:
      rule: "PathPrefix(`/api/v1/search`)"
      service: search-service
      entryPoints:
        - web
      middlewares:
        - cors

    notifications:
      rule: "PathPrefix(`/api/v1/notifications`)"
      service: notification-service
      entryPoints:
        - web
      middlewares:
        - cors

    analytics:
      rule: "PathPrefix(`/api/v1/analytics`)"
      service: analytics-service
      entryPoints:
        - web
      middlewares:
        - cors

  services:
    auth-service:
      loadBalancer:
        servers:
          - url: "http://auth-service:8000"

    course-service:
      loadBalancer:
        servers:
          - url: "http://course-service:8000"

    enrollment-service:
      loadBalancer:
        servers:
          - url: "http://enrollment-service:8000"

    progress-service:
      loadBalancer:
        servers:
          - url: "http://progress-service:8000"

    publishing-service:
      loadBalancer:
        servers:
          - url: "http://publishing-service:8000"

    ai-service:
      loadBalancer:
        servers:
          - url: "http://ai-service:8000"

    search-service:
      loadBalancer:
        servers:
          - url: "http://search-service:8000"

    notification-service:
      loadBalancer:
        servers:
          - url: "http://notification-service:8000"

    analytics-service:
      loadBalancer:
        servers:
          - url: "http://analytics-service:8000"

  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 50

    cors:
      headers:
        accessControlAllowOriginList:
          - "http://localhost:3001"
          - "http://localhost:5173"
        accessControlAllowMethods:
          - "GET"
          - "POST"
          - "PUT"
          - "PATCH"
          - "DELETE"
          - "OPTIONS"
        accessControlAllowHeaders:
          - "Content-Type"
          - "Authorization"
          - "X-Correlation-Id"
          - "Idempotency-Key"
        accessControlMaxAge: 86400
```

## 7. Prometheus Configuration

```yaml
# infra/monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik:8080']

  - job_name: 'auth-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['auth-service:8000']

  - job_name: 'course-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['course-service:8000']

  - job_name: 'enrollment-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['enrollment-service:8000']

  - job_name: 'progress-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['progress-service:8000']

  - job_name: 'publishing-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['publishing-service:8000']

  - job_name: 'ai-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['ai-service:8000']

  - job_name: 'search-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['search-service:8000']

  - job_name: 'notification-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['notification-service:8000']

  - job_name: 'analytics-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['analytics-service:8000']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka:9092']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

## 8. Environment Configuration

### 8.1 `.env.example`

```bash
# ─── General ──────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=DEBUG
SECRET_KEY=change-me-in-production

# ─── PostgreSQL ───────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_HOST_PORT=15432
POSTGRES_PORT=5432
POSTGRES_USER=educorp
POSTGRES_PASSWORD=educorp_dev
POSTGRES_DB=educorp
DATABASE_URL=postgresql+asyncpg://educorp:educorp_dev@postgres:5432/educorp

# ─── MongoDB ──────────────────────────────────────
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_USER=educorp
MONGO_PASSWORD=educorp_dev
MONGO_DB=educorp
MONGO_URL=mongodb://educorp:educorp_dev@mongodb:27017/educorp?authSource=admin

# ─── Redis ────────────────────────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=educorp_dev
REDIS_URL=redis://:educorp_dev@redis:6379/0

# ─── Kafka ────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
SCHEMA_REGISTRY_URL=http://schema-registry:8081
SCHEMA_REGISTRY_HOST_PORT=8082

# ─── RabbitMQ ─────────────────────────────────────
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=educorp
RABBITMQ_PASSWORD=educorp_dev
CELERY_BROKER_URL=amqp://educorp:educorp_dev@rabbitmq:5672//

# ─── Temporal ─────────────────────────────────────
TEMPORAL_HOST=temporal
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=educorp

# ─── MinIO (S3) ──────────────────────────────────
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=educorp
MINIO_SECRET_KEY=educorp_dev
MINIO_BUCKET=course-assets
MINIO_USE_SSL=false

# ─── Qdrant ──────────────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=course_chunks

# ─── AI / LLM ────────────────────────────────────
LLM_BASE_URL=https://nano-gpt.com/api/v1
LLM_API_KEY=change-me
LLM_MODEL=nanogpt-chat
EMBEDDING_BASE_URL=https://nano-gpt.com/api/v1
EMBEDDING_API_KEY=change-me
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536

# ─── JWT ──────────────────────────────────────────
JWT_SECRET_KEY=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── Observability ────────────────────────────────
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=educorp
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# ─── Grafana ──────────────────────────────────────
GRAFANA_PASSWORD=admin

# ─── Feature Flags ────────────────────────────────
INSTRUCTOR_AUTO_APPROVE=false
AI_RETENTION_DAYS=90
```

## 9. Makefile & Build Commands

### 9.1 Linux/macOS (Makefile)

```bash
# Startup (profile-based)
make up                 # Core infra only (~30s)
make up-messaging       # + Kafka, RabbitMQ, Schema Registry
make up-workflow        # + Temporal
make up-app             # + All 9 services + frontend
make up-full            # Everything including observability
make start              # Full orchestrated startup (migrations + seeding)

# Development
make logs SERVICE=auth  # Tail service logs
make health             # Health check all endpoints (formatted table)
make shell SERVICE=auth # Shell into a container
make exec SERVICE=auth CMD="alembic upgrade head"

# Debugging
make debug-service SERVICE=auth  # Attach debugpy on port 5678

# Database
make migrate            # Run all Alembic migrations
make migrate-create SERVICE=auth MSG="add users table"

# Testing
make test SERVICE=auth          # Run tests for a service
make test-coverage SERVICE=auth # With coverage report
make lint                       # Ruff + Mypy

# Maintenance
make down               # Stop all services
make clean              # Remove containers + volumes
make reset              # Full reset: clean → build → start
```

### 9.2 Windows (PowerShell — `make.ps1`)

```powershell
.\make.ps1 up                                  # Core infra
.\make.ps1 up-full                             # Everything
.\make.ps1 start                               # Orchestrated startup
.\make.ps1 logs -Service auth                  # Tail logs
.\make.ps1 health                              # Health check
.\make.ps1 debug-service -Service auth         # Debug with debugpy
.\make.ps1 test -Service auth                  # Run tests
.\make.ps1 migrate-create -Service auth -Msg "add users table"
.\make.ps1 down                                # Stop all
```

## 10. Cross-Platform Development

### 10.1 Windows (Native PowerShell — Recommended)

EduCorp ships PowerShell equivalents of all bash scripts:

| Bash | PowerShell | Purpose |
|------|-----------|---------|
| `make <target>` | `.\make.ps1 <target>` | Build/dev commands |
| `scripts/start-stack.sh` | `scripts/start-stack.ps1` | Orchestrated startup |
| `scripts/dev-setup.sh` | `scripts/dev-setup.ps1` | First-time setup |
| `run-app.sh` | `run-app.ps1` | Quick start |

Requirements:
- Docker Desktop for Windows with Compose v2+
- PowerShell 7+ (recommended) or Windows PowerShell 5.1
- No additional tools needed (`make` not required)

### 10.2 Windows (Alternative — WSL2/Git Bash)

- Use the standard `Makefile` and bash scripts
- Install `make` via `choco install make` or use WSL2 directly
- Volume mounts use forward slashes
- `.env` file uses LF line endings (configured via `.gitattributes`)

### 10.3 Linux/macOS

- Docker Engine + Docker Compose plugin (or Docker Desktop)
- GNU Make (pre-installed on most systems)
- For rootless Docker: ensure volume permissions match UID

### 10.4 `.gitattributes`

```
* text=auto eol=lf
*.sh text eol=lf
*.ps1 text eol=crlf
*.yml text eol=lf
*.yaml text eol=lf
Makefile text eol=lf
.env* text eol=lf
*.sql text eol=lf
*.py text eol=lf
```

## 11. Debugging

### 11.1 Remote Debugging with debugpy

All app services in the `dev` Docker target include `debugpy`. To debug:

```bash
# Linux/macOS
make debug-service SERVICE=auth

# Windows
.\make.ps1 debug-service -Service auth
```

This restarts the service with `debugpy --listen 0.0.0.0:5678 --wait-for-client`, exposing port 5678 on the host.

**VS Code launch configuration** (`.vscode/launch.json`):
```json
{
  "name": "Attach to Service",
  "type": "debugpy",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 },
  "pathMappings": [
    { "localRoot": "${workspaceFolder}/services/auth", "remoteRoot": "/app/service" },
    { "localRoot": "${workspaceFolder}/shared", "remoteRoot": "/app/shared" }
  ]
}
```

### 11.2 Hot Reload

All app services run with `--reload` by default in dev mode. Edit code locally and the service restarts automatically (source directories are bind-mounted).

### 11.3 Container Shell Access

```bash
make shell SERVICE=auth          # Interactive bash shell in the container
make exec SERVICE=auth CMD="python -c 'import app; print(app)'"  # Run a command
```

## 12. Resource Requirements (Development)

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 20 GB free | 40 GB free |
| Docker memory | 6 GB | 10 GB |

### Profile-based resource usage

| Startup Level | Containers | Estimated Memory |
|--------------|------------|-----------------|
| `make up` (infra only) | ~6 | ~2–3 GB |
| `make up-messaging` | ~11 | ~3–4 GB |
| `make up-app` | ~22 | ~5–7 GB |
| `make up-full` | ~25 | ~7–9 GB |

Use `docker stats` to monitor live resource usage.
