#!/usr/bin/env bash
# scripts/start-stack.sh — Robust EduCorp stack startup script.
# Starts infrastructure, waits for health, runs migrations, seeds data,
# and brings up all application services.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Colors ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ─── Prerequisite checks ────────────────────────────────
require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "Missing required command: $1"
        exit 1
    fi
}

require_command docker

if ! docker info >/dev/null 2>&1; then
    fail "Docker daemon is not running"
    exit 1
fi

# ─── .env setup ─────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        info "Created .env from .env.example"
    else
        fail "No .env or .env.example found"
        exit 1
    fi
fi

# ─── Helper: wait for container health ──────────────────
wait_for_healthy() {
    local service="$1"
    local max_wait="${2:-120}"
    local interval=3
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        local health
        health=$(docker compose ps --format json "$service" 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")

        if [ "$health" = "healthy" ]; then
            return 0
        fi

        local state
        state=$(docker compose ps --format json "$service" 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State',''))" 2>/dev/null || echo "")

        if [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
            return 1
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done
    return 1
}

# ─── Helper: wait for a TCP port inside a container ─────
wait_for_port() {
    local service="$1"
    local port="$2"
    local max_wait="${3:-60}"
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        if docker compose exec -T "$service" sh -c "cat < /dev/null > /dev/tcp/localhost/$port 2>/dev/null || nc -z localhost $port 2>/dev/null" 2>/dev/null; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

# ─── Helper: wait for an HTTP endpoint to return 200 ────
wait_for_http() {
    local url="$1"
    local max_wait="${2:-90}"
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        if [ "$code" = "200" ]; then
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    return 1
}

# ─── Helper: run migration for a service ────────────────
run_migration() {
    local service="$1"
    local container="${service}-service"

    # Check if the service has any migration files (beyond .gitkeep)
    local migration_count
    migration_count=$(docker compose exec -T "$container" sh -c \
        "ls alembic/versions/*.py 2>/dev/null | wc -l" 2>/dev/null || echo "0")

    if [ "$migration_count" -gt 0 ]; then
        info "  Running migrations for $service ($migration_count files)..."
        if docker compose exec -T "$container" alembic upgrade head 2>&1; then
            ok "  $service migrations applied"
        else
            warn "  $service migrations failed (non-critical, tables may already exist)"
        fi
    else
        info "  $service: no migration files, skipping"
    fi
}

# ══════════════════════════════════════════════════════════
# PHASE 1: Infrastructure services
# ══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  EduCorp Stack Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

INFRA_SERVICES="postgres mongodb redis qdrant minio zookeeper rabbitmq"
MESSAGING_SERVICES="kafka schema-registry"
WORKFLOW_SERVICES="temporal temporal-ui"
OBSERVABILITY_SERVICES="prometheus grafana jaeger"
GATEWAY_SERVICES="traefik"
APP_SERVICES="auth-service course-service enrollment-service progress-service publishing-service publishing-worker ai-service search-service notification-service notification-worker analytics-service"

info "Phase 1: Starting core infrastructure..."
docker compose up -d $INFRA_SERVICES

info "Waiting for PostgreSQL..."
if wait_for_healthy postgres 60; then
    ok "PostgreSQL is ready"
else
    fail "PostgreSQL failed to start. Check: docker compose logs postgres"
    exit 1
fi

info "Waiting for other infrastructure..."
for svc in mongodb redis minio; do
    if wait_for_healthy "$svc" 60; then
        ok "$svc is ready"
    else
        warn "$svc may not be healthy yet (continuing)"
    fi
done

# ══════════════════════════════════════════════════════════
# PHASE 2: Messaging & workflow services
# ══════════════════════════════════════════════════════════
info "Phase 2: Starting messaging & workflow services..."
docker compose up -d $MESSAGING_SERVICES $WORKFLOW_SERVICES

info "Waiting for Kafka..."
if wait_for_healthy kafka 90; then
    ok "Kafka is ready"
else
    warn "Kafka may not be healthy yet (continuing)"
fi

info "Waiting for RabbitMQ..."
if wait_for_healthy rabbitmq 60; then
    ok "RabbitMQ is ready"
else
    warn "RabbitMQ may not be healthy yet (continuing)"
fi

info "Waiting for Temporal..."
if wait_for_healthy temporal 90; then
    ok "Temporal is ready"
else
    warn "Temporal may not be healthy yet (continuing)"
fi

# ══════════════════════════════════════════════════════════
# PHASE 3: Create Kafka topics
# ══════════════════════════════════════════════════════════
info "Phase 3: Creating Kafka topics..."
if docker compose exec -T kafka bash /opt/kafka-topics.sh 2>&1 | tail -5; then
    ok "Kafka topics created"
else
    warn "Kafka topics creation had issues (may already exist)"
fi

# ══════════════════════════════════════════════════════════
# PHASE 4: Observability & gateway
# ══════════════════════════════════════════════════════════
info "Phase 4: Starting observability & gateway..."
docker compose up -d $OBSERVABILITY_SERVICES $GATEWAY_SERVICES

if wait_for_healthy traefik 30; then
    ok "Traefik gateway is ready"
else
    warn "Traefik may not be healthy yet (continuing)"
fi

# ══════════════════════════════════════════════════════════
# PHASE 5: Application services
# ══════════════════════════════════════════════════════════
info "Phase 5: Starting application services..."
docker compose up -d $APP_SERVICES

info "Waiting for application services to initialize..."
sleep 10

# Wait for auth service first (most critical)
info "Checking auth-service..."
for i in $(seq 1 20); do
    if docker compose exec -T auth-service python -c "import app.main" 2>/dev/null; then
        ok "auth-service is responding"
        break
    fi
    if [ "$i" -eq 20 ]; then
        warn "auth-service may still be starting"
    fi
    sleep 3
done

# ══════════════════════════════════════════════════════════
# PHASE 6: Run migrations
# ══════════════════════════════════════════════════════════
info "Phase 6: Running database migrations..."
for svc in auth course enrollment progress publishing notification analytics; do
    run_migration "$svc"
done
echo ""

# ══════════════════════════════════════════════════════════
# PHASE 7: Seed data
# ══════════════════════════════════════════════════════════
info "Phase 7: Seeding development data..."
if docker compose exec -T auth-service python -m scripts.seed 2>&1; then
    ok "Seed data loaded"
else
    warn "Seeding had issues (data may already exist)"
fi

# ══════════════════════════════════════════════════════════
# PHASE 8: Start frontend
# ══════════════════════════════════════════════════════════
info "Phase 8: Starting frontend..."
docker compose up -d frontend

# ══════════════════════════════════════════════════════════
# PHASE 9: Health check
# ══════════════════════════════════════════════════════════
echo ""
info "Phase 9: Running health checks..."
sleep 5

SERVICES_WITH_HEALTH="auth course enrollment progress publishing ai search notification analytics"
healthy_count=0
total_count=0

for svc in $SERVICES_WITH_HEALTH; do
    total_count=$((total_count + 1))
    endpoint="$svc"
    if [ "$svc" = "notification" ]; then endpoint="notifications"; fi

    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/api/v1/${endpoint}/health/ready" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        ok "  $svc: healthy"
        healthy_count=$((healthy_count + 1))
    else
        warn "  $svc: HTTP $code (may still be starting)"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $healthy_count -eq $total_count ]; then
    echo -e "  ${GREEN}All $total_count services are healthy!${NC}"
else
    echo -e "  ${YELLOW}$healthy_count/$total_count services healthy${NC}"
    echo -e "  ${YELLOW}Some services may still be starting. Run: make health${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  Service          │  URL                               │"
echo "├─────────────────────────────────────────────────────────┤"
echo "│  Gateway          │  http://localhost                   │"
echo "│  Frontend         │  http://localhost:5173              │"
echo "│  Traefik          │  http://localhost:8081              │"
echo "│  Grafana          │  http://localhost:3000              │"
echo "│  Temporal UI      │  http://localhost:8088              │"
echo "│  RabbitMQ         │  http://localhost:15672             │"
echo "│  MinIO            │  http://localhost:9001              │"
echo "│  Jaeger           │  http://localhost:16686             │"
echo "│  Prometheus       │  http://localhost:9090              │"
echo "│  Qdrant           │  http://localhost:6333              │"
echo "│  Schema Registry  │  http://localhost:8082              │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
echo "Commands:"
echo "  docker compose logs -f         # Tail all logs"
echo "  docker compose logs -f <svc>   # Tail specific service"
echo "  make health                    # Check service health"
echo "  make down                      # Stop everything"
echo ""
