# Makefile — Developer shortcuts
.PHONY: help up down restart logs build test migrate seed clean start

COMPOSE=docker compose
SERVICE?=

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ──────────────────────────────────────
start: ## Full startup: infra → migrations → seed → services (recommended)
	@bash scripts/start-stack.sh

up: ## Start all services (docker compose up -d)
	$(COMPOSE) up -d

up-infra: ## Start infrastructure only
	$(COMPOSE) up -d postgres mongodb redis qdrant minio kafka zookeeper schema-registry rabbitmq temporal temporal-ui prometheus grafana jaeger traefik

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all (or specific SERVICE=name)
	$(COMPOSE) restart $(SERVICE)

logs: ## Tail logs (or specific SERVICE=name)
	$(COMPOSE) logs -f $(SERVICE)

build: ## Build all service images
	$(COMPOSE) build

build-service: ## Build single service (SERVICE=auth)
	$(COMPOSE) build $(SERVICE)-service

ps: ## Show container status
	$(COMPOSE) ps

health: ## Check health of all services
	@for svc in auth course enrollment progress publishing ai search notification analytics; do \
		endpoint=$$svc; \
		if [ "$$svc" = "course" ]; then endpoint="courses"; fi; \
		if [ "$$svc" = "enrollment" ]; then endpoint="enrollments"; fi; \
		if [ "$$svc" = "notification" ]; then endpoint="notifications"; fi; \
		printf "%-20s" "$$svc-service:"; \
		curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/$$endpoint/health/ready 2>/dev/null || echo "DOWN"; \
		echo; \
	done

# ─── Database ────────────────────────────────────
migrate: ## Run all migrations (skips services with no migration files)
	@for svc in auth course enrollment progress publishing notification analytics; do \
		count=$$($(COMPOSE) exec -T $$svc-service sh -c "ls alembic/versions/*.py 2>/dev/null | wc -l" 2>/dev/null || echo 0); \
		if [ "$$count" -gt 0 ]; then \
			echo "=== Migrating $$svc ($$count files) ==="; \
			$(COMPOSE) exec -T $$svc-service alembic upgrade head || echo "  ⚠ $$svc migration failed"; \
		else \
			echo "=== $$svc: no migrations, skipping ==="; \
		fi; \
	done

migrate-service: ## Run migration for single service (SERVICE=auth)
	$(COMPOSE) exec $(SERVICE)-service alembic upgrade head

migrate-create: ## Create new migration (SERVICE=auth MSG="add users table")
	$(COMPOSE) exec $(SERVICE)-service alembic revision --autogenerate -m "$(MSG)"

# ─── Kafka ───────────────────────────────────────
kafka-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka bash /opt/kafka-topics.sh

kafka-list: ## List Kafka topics
	$(COMPOSE) exec kafka kafka-topics --bootstrap-server localhost:29092 --list

# ─── Testing ─────────────────────────────────────
test: ## Run all tests
	@for svc in auth course enrollment progress publishing ai search notification analytics; do \
		echo "=== Testing $$svc ==="; \
		$(COMPOSE) exec $$svc-service pytest tests/ -v; \
	done

test-service: ## Run tests for single service (SERVICE=auth)
	$(COMPOSE) exec $(SERVICE)-service pytest tests/ -v

lint: ## Run linting (ruff + mypy)
	uv run ruff check .
	uv run mypy .

fmt: ## Format code
	uv run ruff format .

# ─── Seeding ─────────────────────────────────────
seed: ## Seed development data
	$(COMPOSE) exec auth-service python -m scripts.seed

# ─── Cleanup ─────────────────────────────────────
clean: ## Remove all containers and volumes
	$(COMPOSE) down -v --remove-orphans

reset: ## Full reset: clean + rebuild + start fresh
	$(MAKE) clean
	$(MAKE) build
	@bash scripts/start-stack.sh
	$(MAKE) kafka-topics
	$(MAKE) seed
