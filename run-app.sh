#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

WEB_PID=""

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
}

wait_for_url() {
    local url="$1"
    local label="$2"
    local attempts="${3:-60}"
    local delay_seconds="${4:-2}"
    local attempt

    for attempt in $(seq 1 "$attempts"); do
        if curl --fail --silent "$url" >/dev/null 2>&1; then
            echo "$label is ready"
            return 0
        fi
        echo "Waiting for $label ($attempt/$attempts)"
        sleep "$delay_seconds"
    done

    echo "$label did not become ready: $url" >&2
    return 1
}

cleanup() {
    if [ -n "$WEB_PID" ] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
        kill "$WEB_PID" >/dev/null 2>&1 || true
        wait "$WEB_PID" >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT INT TERM

require_command bash
require_command curl
require_command docker
require_command make
require_command npm

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

echo "Starting backend stack"
bash ./scripts/dev-setup.sh

echo "Running database migrations"
make migrate

echo "Waiting for gateway routes"
wait_for_url "http://localhost/api/v1/auth/health/ready" "auth service"
wait_for_url "http://localhost/api/v1/courses/health/ready" "course service"

if [ ! -d apps/web/node_modules ]; then
    echo "Installing web dependencies"
    npm --prefix apps/web install
fi

echo "Starting frontend dev server"
npm --prefix apps/web run dev -- --host 0.0.0.0 &
WEB_PID="$!"

echo ""
echo "EduCorp is running"
echo "Gateway:   http://localhost"
echo "Frontend:  http://localhost:5173"
echo "Traefik:   http://localhost:8081"
echo "Grafana:   http://localhost:3000"
echo "Temporal:  http://localhost:8088"
echo "RabbitMQ:  http://localhost:15672"
echo "MinIO:     http://localhost:9001"
echo "Jaeger:    http://localhost:16686"
echo ""
echo "Press Ctrl+C to stop the frontend dev server. Docker services stay running until you call 'make down'."

wait "$WEB_PID"