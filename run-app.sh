#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
}

require_command docker
require_command make

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

echo "Starting EduCorp stack..."
docker compose up -d

echo ""
echo "EduCorp is running"
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│ Service         │ URL                                  │"
echo "├─────────────────────────────────────────────────────────┤"
echo "│ Gateway         │ http://localhost                      │"
echo "│ Frontend       │ http://localhost:5173                 │"
echo "│ Traefik        │ http://localhost:8081                 │"
echo "│ Grafana        │ http://localhost:3000                 │"
echo "│ Temporal UI    │ http://localhost:8088                 │"
echo "│ RabbitMQ       │ http://localhost:15672                │"
echo "│ MinIO          │ http://localhost:9001                 │"
echo "│ Jaeger         │ http://localhost:16686                │"
echo "│ Prometheus     │ http://localhost:9090                 │"
echo "│ Qdrant         │ http://localhost:6333                 │"
echo "│ Schema Reg.    │ http://localhost:8082                 │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
echo "Run 'docker compose logs -f' to view logs."
echo "Run 'make down' to stop all services."
