#!/usr/bin/env bash
# scripts/start-stack.sh — EduCorp orchestrated startup
# Starts services in dependency order with parallel waits where possible.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Colors ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

elapsed() {
    local start=$1
    local now=$(date +%s)
    echo "$((now - start))s"
}

# ─── Prerequisite checks ────────────────────────────────
command -v docker >/dev/null 2>&1 || { fail "Missing: docker"; exit 1; }
docker info >/dev/null 2>&1 || { fail "Docker daemon not running"; exit 1; }

# ─── .env setup ─────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        info "Created .env from .env.example"
    else
        fail "No .env or .env.example found"; exit 1
    fi
fi

# ─── Wait helpers ────────────────────────────────────────
wait_for_healthy() {
    local service="$1" max_wait="${2:-90}" interval=2 elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        local cid
        cid=$(docker compose ps -q "$service" 2>/dev/null || true)
        [ -z "$cid" ] && { sleep $interval; elapsed=$((elapsed + interval)); continue; }

        local health
        health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$cid" 2>/dev/null || echo "unknown")

        case "$health" in
            healthy|running) return 0 ;;
            unhealthy)       return 1 ;;
        esac
        sleep $interval; elapsed=$((elapsed + interval))
    done
    return 1
}

wait_parallel() {
    local timeout="${1}"; shift
    local services=("$@")
    local pids=()

    for svc in "${services[@]}"; do
        ( wait_for_healthy "$svc" "$timeout" ) &
        pids+=($!)
    done

    local all_ok=true
    for i in "${!pids[@]}"; do
        if wait "${pids[$i]}" 2>/dev/null; then
            ok "  ${services[$i]} ready"
        else
            warn "  ${services[$i]} may not be healthy"
            all_ok=false
        fi
    done
    $all_ok
}

run_migration() {
    local svc="$1" container="${1}-service"
    local count
    count=$(docker compose exec -T "$container" sh -c \
        "ls alembic/versions/*.py 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    if [ "$count" -gt 0 ]; then
        info "  Migrating $svc ($count files)..."
        docker compose exec -T "$container" alembic upgrade head
        ok "  $svc migrations applied"
    else
        info "  $svc: no migrations, skipping"
    fi
}

# ══════════════════════════════════════════════════════════
START_TIME=$(date +%s)
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  EduCorp Stack Startup${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Phase 1: Core infrastructure (parallel) ──────────────
info "Phase 1/6: Core infrastructure..."
docker compose up -d postgres mongodb redis qdrant minio traefik

info "Waiting for core services (parallel)..."
wait_parallel 60 postgres mongodb redis qdrant minio || {
    fail "Core infrastructure did not become healthy"
    exit 1
}
ok "Core infrastructure ready ($(elapsed $START_TIME))"

# ── Phase 2: Messaging (parallel) ────────────────────────
info "Phase 2/6: Messaging services..."
docker compose --profile messaging up -d

info "Waiting for messaging (parallel)..."
wait_parallel 90 kafka rabbitmq || {
    fail "Messaging services did not become healthy"
    exit 1
}
ok "Messaging ready ($(elapsed $START_TIME))"

# ── Phase 3: Workflow engine ─────────────────────────────
info "Phase 3/6: Workflow engine..."
docker compose --profile workflow up -d

info "Waiting for Temporal..."
if wait_for_healthy temporal 90; then
    ok "Temporal ready ($(elapsed $START_TIME))"
else
    fail "Temporal did not become healthy"
    exit 1
fi

# ── Phase 4: Application services (all at once) ─────────
info "Phase 4/6: Application services..."
docker compose --profile app up -d

info "Waiting for services to initialize..."
sleep 8

# ── Phase 5: Migrations ─────────────────────────────────
info "Phase 5/6: Database migrations..."
for svc in auth course enrollment progress publishing notification analytics; do
    run_migration "$svc"
done

# ── Phase 6: Seed + health ──────────────────────────────
info "Phase 6/6: Seeding data..."
docker compose exec -T auth-service python -m scripts.seed >/dev/null
ok "Auth admin seed complete"
uv run python scripts/seed_data.py
ok "Seed data loaded"

echo ""
info "Running health checks..."
sleep 3

healthy=0; total=0
for svc in auth course enrollment progress publishing ai search notification analytics; do
    total=$((total + 1))
    endpoint="$svc"
    case "$svc" in
        course) endpoint="courses" ;;
        enrollment) endpoint="enrollments" ;;
        notification) endpoint="notifications" ;;
    esac
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://localhost/api/v1/${endpoint}/health/ready" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        ok "  $svc: healthy"; healthy=$((healthy + 1))
    else
        warn "  $svc: HTTP $code"
    fi
done

TOTAL_TIME=$(elapsed $START_TIME)
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $healthy -eq $total ]; then
    echo -e "  ${GREEN}${BOLD}All $total services healthy${NC} (${TOTAL_TIME})"
else
    echo -e "  ${RED}${BOLD}$healthy/$total services healthy${NC} (${TOTAL_TIME})"
    echo -e "  Run: ${BOLD}make health${NC} to inspect failures"
    exit 1
fi
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "┌──────────────────┬──────────────────────────────────┐"
echo "│  Service         │  URL                             │"
echo "├──────────────────┼──────────────────────────────────┤"
echo "│  Gateway         │  http://localhost                 │"
echo "│  Frontend        │  http://localhost:5173            │"
echo "│  Traefik Dash    │  http://localhost:8081            │"
echo "│  Grafana         │  http://localhost:3000            │"
echo "│  Temporal UI     │  http://localhost:8088            │"
echo "│  RabbitMQ Mgmt   │  http://localhost:15672           │"
echo "│  MinIO Console   │  http://localhost:9001            │"
echo "│  Jaeger          │  http://localhost:16686           │"
echo "│  Prometheus      │  http://localhost:9090            │"
echo "│  Qdrant          │  http://localhost:6333            │"
echo "│  Schema Registry │  http://localhost:8082            │"
echo "└──────────────────┴──────────────────────────────────┘"
echo ""
echo "Commands:"
echo "  make logs                    # Tail all logs"
echo "  make logs SERVICE=auth       # Tail specific service"
echo "  make health                  # Check service health"
echo "  make shell SERVICE=auth      # Shell into service"
echo "  make debug-service SERVICE=auth  # Debug with debugpy"
echo "  make down                    # Stop everything"
echo ""
