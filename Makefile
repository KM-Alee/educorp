# Makefile — EduCorp Developer Shortcuts
# Run `make help` to see all available targets
.PHONY: help up up-full up-messaging up-workflow up-observability up-app \
        down restart logs build ps health \
        migrate migrate-service migrate-create \
        kafka-topics kafka-list \
        test test-service test-coverage lint fmt \
        seed shell exec \
        clean reset debug-service

COMPOSE = docker compose
SERVICE ?=
MSG ?=

# ─── Service lists ───────────────────────────────
SERVICES = auth course enrollment progress publishing ai search notification analytics
MIGRATE_SERVICES = auth course enrollment progress publishing notification analytics

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ─── Docker Compose ──────────────────────────────
start: ## Full startup: infra → messaging → workflow → app (recommended)
	@bash scripts/start-stack.sh

up: ## Start core infrastructure only (fast, ~30s)
	$(COMPOSE) up -d

up-messaging: ## Start core + messaging (Kafka, RabbitMQ)
	$(COMPOSE) --profile messaging up -d

up-workflow: ## Start core + messaging + workflow (Temporal)
	$(COMPOSE) --profile messaging --profile workflow up -d

up-observability: ## Start core + observability (Prometheus, Grafana, Jaeger)
	$(COMPOSE) --profile observability up -d

up-app: ## Start core + messaging + workflow + app services
	$(COMPOSE) --profile messaging --profile workflow --profile app up -d

up-full: ## Start everything including observability
	$(COMPOSE) --profile full up -d

down: ## Stop all services
	$(COMPOSE) --profile full down

restart: ## Restart all or specific SERVICE=<name>
	@if [ -n "$(SERVICE)" ]; then \
		$(COMPOSE) restart $(SERVICE)-service; \
	else \
		$(COMPOSE) --profile full restart; \
	fi

logs: ## Tail logs (all or SERVICE=<name>)
	@if [ -n "$(SERVICE)" ]; then \
		$(COMPOSE) logs -f --tail=100 $(SERVICE)-service; \
	else \
		$(COMPOSE) --profile full logs -f --tail=50; \
	fi

build: ## Build all service images
	DOCKER_BUILDKIT=1 $(COMPOSE) --profile full build

build-service: ## Build single service (SERVICE=auth)
	DOCKER_BUILDKIT=1 $(COMPOSE) build $(SERVICE)-service

ps: ## Show container status
	$(COMPOSE) --profile full ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

health: ## Check health of all services
	@echo ""; \
	printf "\033[1m%-22s %-10s %s\033[0m\n" "SERVICE" "STATUS" "RESPONSE"; \
	echo "──────────────────────────────────────────────────"; \
	for svc in $(SERVICES); do \
		endpoint=$$svc; \
		case $$svc in \
			course) endpoint="courses" ;; \
			enrollment) endpoint="enrollments" ;; \
			notification) endpoint="notifications" ;; \
		esac; \
		code=$$(curl -s -o /dev/null -w "%{http_code}" \
			http://localhost/api/v1/$$endpoint/health/ready 2>/dev/null || echo "000"); \
		if [ "$$code" = "200" ]; then \
			printf "  %-20s \033[32m%-10s\033[0m %s\n" "$$svc" "healthy" "HTTP $$code"; \
		else \
			printf "  %-20s \033[31m%-10s\033[0m %s\n" "$$svc" "down" "HTTP $$code"; \
		fi; \
	done; \
	echo ""

# ─── Database ────────────────────────────────────
migrate: ## Run all migrations
	@for svc in $(MIGRATE_SERVICES); do \
		count=$$($(COMPOSE) exec -T $$svc-service sh -c \
			"ls alembic/versions/*.py 2>/dev/null | wc -l" 2>/dev/null || echo 0); \
		if [ "$$count" -gt 0 ]; then \
			echo "=== Migrating $$svc ($$count files) ==="; \
			$(COMPOSE) exec -T $$svc-service alembic upgrade head || \
				echo "  ⚠ $$svc migration failed"; \
		else \
			echo "=== $$svc: no migrations, skipping ==="; \
		fi; \
	done

migrate-service: ## Run migration for SERVICE=<name>
	$(COMPOSE) exec $(SERVICE)-service alembic upgrade head

migrate-create: ## Create migration (SERVICE=auth MSG="add users table")
	$(COMPOSE) exec $(SERVICE)-service alembic revision --autogenerate -m "$(MSG)"

# ─── Kafka ───────────────────────────────────────
kafka-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka bash /opt/kafka-topics.sh

kafka-list: ## List Kafka topics
	$(COMPOSE) exec kafka kafka-topics --bootstrap-server localhost:29092 --list

# ─── Testing ─────────────────────────────────────
test: ## Run all tests
	@for svc in $(SERVICES); do \
		echo "=== Testing $$svc ==="; \
		$(COMPOSE) exec -T $$svc-service pytest tests/ -v --tb=short || true; \
	done

test-service: ## Run tests for SERVICE=<name>
	$(COMPOSE) exec $(SERVICE)-service pytest tests/ -v

test-coverage: ## Run tests with coverage for SERVICE=<name>
	$(COMPOSE) exec $(SERVICE)-service pytest tests/ -v --cov=app --cov-report=term-missing

lint: ## Run linting (ruff + mypy)
	uv run ruff check .
	uv run mypy .

fmt: ## Format code
	uv run ruff format .
	uv run ruff check --fix .

# ─── Seeding ─────────────────────────────────────
seed: ## Seed development data
	$(COMPOSE) exec auth-service python -m scripts.seed

# ─── Developer Utilities ─────────────────────────
shell: ## Open shell in SERVICE=<name> container
	$(COMPOSE) exec $(SERVICE)-service /bin/bash

exec: ## Run command in SERVICE container (SERVICE=auth CMD="alembic history")
	$(COMPOSE) exec $(SERVICE)-service $(CMD)

debug-service: ## Start SERVICE with debugpy (attach on port 5678)
	$(COMPOSE) stop $(SERVICE)-service 2>/dev/null || true
	$(COMPOSE) run --rm -p 5678:5678 --name $(SERVICE)-debug \
		$(SERVICE)-service python -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
		-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ─── Cleanup ─────────────────────────────────────
clean: ## Remove all containers and volumes
	$(COMPOSE) --profile full down -v --remove-orphans

reset: ## Full reset: clean + rebuild + start fresh
	$(MAKE) clean
	$(MAKE) build
	$(MAKE) start
