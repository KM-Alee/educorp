#!/usr/bin/env bash
set -euo pipefail

echo "=== EduCorp Development Setup ==="

# 1. Copy .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists, skipping"
fi

# 2. Build containers
echo "Building containers..."
docker compose build

# 3. Start infrastructure
echo "Starting all services..."
docker compose up -d

# 4. Wait for core infrastructure only
echo "Waiting for core infrastructure services to become healthy..."
monitored_services="postgres mongodb redis qdrant minio kafka rabbitmq temporal"
for i in $(seq 1 60); do
    healthy=0
    total=0
    for service in $monitored_services; do
        total=$((total + 1))
        container_id=$(docker compose ps -q "$service" 2>/dev/null || true)
        if [ -z "$container_id" ]; then
            continue
        fi
        status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)
        if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
            healthy=$((healthy + 1))
        fi
    done
    echo "  Health check $i/60: ~$healthy/$total healthy"
    if [ "$healthy" -ge "$total" ] && [ "$total" -gt 0 ]; then
        break
    fi
    sleep 5
done

# 5. Create Kafka topics
echo "Creating Kafka topics..."
docker compose exec -T kafka bash /opt/kafka-topics.sh || echo "Topics may already exist"

echo ""
echo "=== Setup Complete ==="
echo "Services:   http://localhost (via Traefik)"
echo "Grafana:    http://localhost:3000 (admin/admin)"
echo "Temporal:   http://localhost:8088"
echo "RabbitMQ:   http://localhost:15672 (educorp/educorp_dev)"
echo "MinIO:      http://localhost:9001 (educorp/educorp_dev)"
echo "Jaeger:     http://localhost:16686"
echo "Traefik:    http://localhost:8080"
