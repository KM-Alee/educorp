# EduCorp — System Architecture

## 1. Architecture Overview

EduCorp is a **service-oriented platform** composed of a first-party web application and domain-bounded backend services communicating through synchronous APIs (HTTP/REST) and asynchronous events (Kafka). Complex multi-step workflows (publishing, enrollment sagas) are orchestrated by Temporal. The system follows a **CQRS-lite** pattern: PostgreSQL is the system of record for transactional writes, while derived read models (Qdrant, search indexes, analytics projections) power query-heavy paths.

```
┌───────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                 │
│  (EduCorp Web App / Mobile App later / API Consumers)                │
└──────────────────────────┬────────────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      API Gateway (Traefik)                            │
│  - TLS termination                                                    │
│  - Rate limiting (global)                                             │
│  - Request routing by path prefix                                     │
│  - CORS, request ID injection                                         │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────────────┘
       │      │      │      │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
   ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
   │ Auth ││Course││Enroll││Progr.││Publi.││  AI  ││Search││Notif.│
   │ Svc  ││ Svc  ││ Svc  ││ Svc  ││ Svc  ││ Svc  ││ Svc  ││ Svc  │
   └──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
      │       │       │       │       │       │       │       │
      ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    Data & Infrastructure Layer                │
   │  PostgreSQL │ MongoDB │ Redis │ Qdrant │ MinIO │ Kafka       │
   │  Temporal   │ RabbitMQ│ Schema Registry                      │
   └──────────────────────────────────────────────────────────────┘
```

## 2. Service Decomposition

### 2.1 Service Inventory

| Service | Domain | Primary DB | Port (dev) | Description |
|---------|--------|-----------|------------|-------------|
| **auth-service** | Identity & Access | PostgreSQL | 8001 | Registration, login, JWT, RBAC, user management |
| **course-service** | Content Authoring | PostgreSQL + MongoDB | 8002 | Course CRUD, modules, assets, drafts, validation |
| **enrollment-service** | Enrollment | PostgreSQL | 8003 | Enrollment, prerequisites, capacity, idempotency |
| **progress-service** | Learning Progress | PostgreSQL | 8004 | Progress tracking, completion, certificates |
| **publishing-service** | Content Pipeline | PostgreSQL + Qdrant | 8005 | Temporal workflows: extract → chunk → embed → index |
| **ai-service** | AI/LLM | Redis (cache) | 8006 | RAG Q&A, instructor tools, LangChain/LangGraph |
| **search-service** | Discovery | Qdrant + PostgreSQL | 8007 | Catalog browse, keyword search, semantic retrieval |
| **notification-service** | Notifications | PostgreSQL + Redis | 8008 | Celery workers, email, in-app notifications |
| **analytics-service** | Reporting | PostgreSQL | 8009 | Event consumers, aggregation, dashboards |

### 2.2 Service Communication Matrix

| From → To | Method | Description |
|-----------|--------|-------------|
| Client → Any Service | HTTP REST (via gateway) | All client-facing operations |
| auth-service → Kafka | Outbox → Kafka | UserCreated, RoleChanged events |
| course-service → Kafka | Outbox → Kafka | CourseDraftUpdated events |
| enrollment-service → Kafka | Outbox → Kafka | EnrollmentCreated, EnrollmentCancelled |
| progress-service → Kafka | Outbox → Kafka | ProgressUpdated, CourseCompleted |
| publishing-service → Temporal | Temporal Client | Start/query publishing workflows |
| publishing-service → Qdrant | gRPC/HTTP | Write embeddings and chunks |
| publishing-service → Kafka | Outbox → Kafka | CoursePublishRequested, CourseReady, CoursePublishFailed |
| ai-service → Qdrant | gRPC/HTTP | Semantic retrieval (read) |
| ai-service → LLM Provider | HTTPS | Chat completions, embeddings |
| ai-service → Kafka | Direct produce | AssistantQueryAsked, AssistantAnswerGenerated |
| notification-service ← Kafka | Consumer | Listens for events to trigger notifications |
| notification-service → RabbitMQ | Celery task | Email/push delivery jobs |
| analytics-service ← Kafka | Consumer | Aggregate all domain events |
| Any service → auth-service | HTTP (internal) | Token validation, user lookup (or JWT self-validation) |
| Any service → Redis | TCP | Caching, rate limits, idempotency keys |

### 2.3 First-Party Web App

EduCorp now includes a first-party web frontend in `apps/web`. The web app is delivered in lockstep with backend phases instead of waiting for backend completion.

**Responsibilities**
- Authentication and session lifecycle: register, login, refresh, logout, verify email, password reset
- Role-aware navigation for student, instructor, and admin experiences
- CRUD orchestration against the public REST APIs exposed through Traefik
- Displaying correlation-aware error states from the standard response envelope

**Frontend architecture principles**
- **Direct API consumption through Traefik**: the browser calls `/api/v1/*` endpoints directly; there is no separate BFF in Phase 1.
- **Route-level authorization**: protected routes require a valid access token and role checks in the client before rendering privileged screens.
- **Session resilience**: access tokens are short-lived; refresh is handled centrally by the frontend API client.
- **Progressive complexity**: Phase 1 focuses on auth and admin workflows, while course authoring, enrollment, and learner progress UI arrive in later phases.

**Design adaptation**
- The frontend uses a warm editorial visual language derived from `cursor-inspo.md`, but adapted for a productivity application rather than a marketing site.
- Keep surfaces cream-toned, borders warm and restrained, typography expressive, and motion subtle.
- Avoid gratuitous gradients, glow, glassmorphism, or AI-themed chrome. The product should feel operational, not promotional.

## 3. Data Architecture

### 3.1 System of Record (PostgreSQL)

PostgreSQL serves as the **single source of truth** for all transactional data. Each service owns its schema (schema-per-service pattern within a shared PostgreSQL cluster for dev simplicity, separate instances in production).

| Schema | Owner Service | Tables |
|--------|--------------|--------|
| `auth` | auth-service | users, roles, user_roles, refresh_tokens, password_resets, audit_log |
| `course` | course-service | courses, modules, assets, course_metadata |
| `enrollment` | enrollment-service | enrollments, enrollment_audit |
| `progress` | progress-service | student_progress, module_progress, certificates |
| `publishing` | publishing-service | course_versions, publishing_jobs, outbox |
| `notification` | notification-service | notifications, notification_preferences |
| `analytics` | analytics-service | event_store, daily_aggregates, course_metrics |

### 3.2 Content Store (MongoDB)

MongoDB stores **flexible, schema-evolving content** that doesn't fit well in relational tables:
- Course draft JSON (rich editor content, nested structures)
- Asset extraction results (parsed text, metadata)
- AI job inputs/outputs
- Notification templates

### 3.3 Cache Layer (Redis)

Redis serves multiple roles:
- **API response caching** — catalog listings, course metadata (TTL: 5 min)
- **Rate limiting** — sliding window counters per user/endpoint
- **Idempotency keys** — store request hashes with TTL for deduplication
- **Session data** — refresh token blacklist
- **Distributed locks** — enrollment capacity checks

### 3.4 Vector Store (Qdrant)

Qdrant stores embeddings with rich metadata for semantic search:
- **Collection per course** (or shared collection with course_id filtering)
- **Payload metadata**: course_id, version_id, module_id, asset_id, chunk_index, text
- **Only READY version chunks are queryable** (enforced by metadata filter)
- **Indexing**: HNSW for approximate nearest neighbors

### 3.5 Object Storage (MinIO / S3)

Stores raw uploaded files:
- Bucket: `course-assets/{course_id}/{version_id}/{asset_id}/{filename}`
- Presigned URLs for secure upload/download
- Lifecycle policies for cleanup of failed version assets

## 4. Event Architecture

### 4.1 Kafka Topology

**Cluster**: 3 brokers (production), 1 broker (development)

| Topic | Partitions | Key | Producers | Consumers |
|-------|-----------|-----|-----------|-----------|
| `user.lifecycle` | 6 | user_id | auth-service | analytics, notification |
| `course.lifecycle` | 12 | course_id | course-service, publishing-service | analytics, notification, search |
| `enrollment.lifecycle` | 12 | enrollment_id | enrollment-service | analytics, notification, progress |
| `progress.lifecycle` | 12 | enrollment_id | progress-service | analytics, notification |
| `ai.usage` | 6 | user_id | ai-service | analytics |
| `notification.requests` | 6 | user_id | any service | notification-service |

### 4.2 Transactional Outbox Pattern

All services that produce Kafka events use the **transactional outbox pattern**:

1. Business operation and outbox row are written in the **same database transaction**.
2. A **Debezium CDC connector** (or a polling relay) reads the outbox table and publishes to Kafka.
3. The outbox table schema:

```sql
CREATE TABLE outbox (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,  -- e.g., 'enrollment'
    aggregate_id   UUID NOT NULL,
    event_type    VARCHAR(100) NOT NULL,   -- e.g., 'EnrollmentCreated'
    payload       JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at  TIMESTAMPTZ,             -- NULL until relayed
    correlation_id UUID NOT NULL
);
```

### 4.3 Schema Registry

All Kafka message values are registered in Confluent Schema Registry:
- **Format**: JSON Schema (simpler tooling for Python ecosystem)
- **Compatibility mode**: BACKWARD (consumers can handle older schemas)
- **Naming convention**: `{topic}-value` (e.g., `enrollment.lifecycle-value`)

### 4.4 Dead Letter Queues

Each consumer group has a corresponding DLQ topic:
- Pattern: `{topic}.dlq` (e.g., `enrollment.lifecycle.dlq`)
- Messages land in DLQ after **3 retries** with exponential backoff
- Ops dashboard surfaces DLQ depth and allows replay

## 5. Workflow Architecture (Temporal)

### 5.1 Publishing Workflow

The most complex workflow in the system. Orchestrated by Temporal for durability, visibility, and retry semantics.

```
PublishCourseWorkflow(course_id, version_id, initiated_by)
│
├── Activity: ValidateAssets
│   └── Check all assets exist in MinIO, formats supported
│
├── Activity: ExtractText (per asset, parallel)
│   └── PDF → text, DOCX → text, PPTX → text, etc.
│
├── Activity: NormalizeAndChunk
│   └── Clean text, split into chunks with metadata
│
├── Activity: GenerateEmbeddings (batched)
│   └── Call embedding API, store in Qdrant
│
├── Activity: IndexForSearch
│   └── Update keyword search indexes
│
├── Activity: MarkVersionReady
│   └── UPDATE course_versions SET status = 'READY'
│   └── Emit CourseReady event via outbox
│
└── On Failure at any step:
    └── Activity: MarkVersionFailed(step, error)
    └── Emit CoursePublishFailed event
    └── Previous READY version remains live
```

**Temporal Configuration:**
- Namespace: `educorp`
- Task Queue: `publishing-tasks`
- Workflow timeout: 2 hours (configurable)
- Activity retries: 3 attempts, backoff coefficient 2.0
- Heartbeat: every 30s for long-running activities

### 5.2 Enrollment Saga (Optional Temporal)

For complex enrollment with prerequisites + capacity + progress initialization:

```
EnrollStudentWorkflow(student_id, course_id, idempotency_key)
│
├── Activity: CheckPrerequisites
├── Activity: ReserveCapacity (with distributed lock)
├── Activity: CreateEnrollmentRecord
├── Activity: InitializeProgress
├── Activity: EmitEnrollmentEvent
│
└── Compensation on failure:
    └── ReleaseCapacity
    └── CleanupPartialRecords
```

## 6. Authentication & Authorization Flow

### 6.1 JWT Architecture

```
Client                  Gateway              Auth Service            Target Service
  │                       │                       │                       │
  │── POST /auth/login ──▶│──────────────────────▶│                       │
  │                       │                       │── validate creds      │
  │                       │                       │── generate tokens     │
  │◀── {access, refresh}──│◀──────────────────────│                       │
  │                       │                       │                       │
  │── GET /courses ──────▶│                       │                       │
  │   Authorization:      │── validate JWT ──────▶│                       │
  │   Bearer <token>      │◀── {user_id, roles} ──│                       │
  │                       │──────────────────────────────────────────────▶│
  │                       │                       │                       │── check role
  │◀── courses[] ─────────│◀──────────────────────────────────────────────│
```

- **Access token**: short-lived (15 min), contains user_id + roles in claims
- **Refresh token**: long-lived (7 days), stored in DB, rotated on use
- **Token validation**: gateway validates JWT signature and expiry; services trust the claims
- **Role claims**: `["student"]`, `["instructor"]`, `["admin"]`

### 6.2 Entitlement Checks

For content access:
1. Gateway validates JWT → passes `X-User-Id` and `X-User-Roles` headers to services.
2. Target service verifies **entitlement**: enrolled in course OR admin OR instructor-owner.
3. AI service additionally checks that the queried version is **READY**.

## 7. Deployment Topology

### 7.1 Development (Docker Compose)

All services + infrastructure run in a single Docker Compose stack:

```yaml
# Service containers
auth-service, course-service, enrollment-service, progress-service,
publishing-service, ai-service, search-service, notification-service,
analytics-service

# Infrastructure containers
postgresql, mongodb, redis, qdrant, minio,
kafka (+ zookeeper), schema-registry,
temporal (+ temporal-ui),
rabbitmq,
prometheus, grafana, jaeger,
traefik
```

### 7.2 Network Architecture

```
┌─ educorp-network (bridge) ──────────────────────────────────┐
│                                                                  │
│  ┌─ frontend ─┐  ┌─ backend ──────────────────────────────────┐ │
│  │  traefik    │  │  auth  course  enrollment  progress       │ │
│  │  (ports:    │  │  publishing  ai  search  notification     │ │
│  │   80, 443)  │  │  analytics                                │ │
│  └─────────────┘  └──────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ data ─────────────────────────────────────────────────────┐ │
│  │  postgresql  mongodb  redis  qdrant  minio                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ messaging ────────────────────────────────────────────────┐ │
│  │  kafka  zookeeper  schema-registry  rabbitmq  temporal     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ observability ────────────────────────────────────────────┐ │
│  │  prometheus  grafana  jaeger                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 8. Cross-Cutting Concerns

### 8.1 Correlation IDs

Every inbound request receives a `X-Correlation-Id` (generated by gateway if not present). This ID:
- Propagates through all inter-service calls (HTTP headers)
- Attaches to all Kafka messages
- Attaches to all Temporal workflow context
- Appears in all structured log entries
- Is returned in API error responses for support reference

### 8.2 Error Response Format

All services use a uniform error response:

```json
{
  "error": {
    "code": "ENROLLMENT_CAPACITY_EXCEEDED",
    "message": "Course has reached maximum enrollment capacity",
    "details": {
      "course_id": "uuid",
      "current_capacity": 100,
      "max_capacity": 100
    },
    "correlation_id": "uuid",
    "timestamp": "2026-04-11T12:00:00Z"
  }
}
```

### 8.3 API Versioning

- URL prefix versioning: `/api/v1/...`
- Breaking changes → new version prefix
- Deprecation: 6-month sunset with `Sunset` header

### 8.4 Health Checks

Every service exposes:
- `GET /health/live` — is the process running? (always 200 if reachable)
- `GET /health/ready` — can it serve traffic? (checks DB, cache, dependencies)

### 8.5 Graceful Shutdown

All services handle `SIGTERM`:
1. Stop accepting new requests
2. Drain in-flight requests (30s timeout)
3. Close DB connections, Kafka producers, etc.
4. Exit

## 9. Scalability Considerations

### 9.1 Horizontal Scaling

| Service | Scaling Strategy | Bottleneck |
|---------|-----------------|------------|
| auth-service | Stateless, scale freely | Token validation is CPU-bound |
| course-service | Stateless, scale freely | MongoDB write throughput |
| enrollment-service | Scale with care (capacity locks) | PostgreSQL row locks |
| publishing-service | Scale Temporal workers | LLM API rate limits |
| ai-service | Scale freely (stateless) | LLM API rate limits, Qdrant read |
| search-service | Scale freely | Qdrant query throughput |
| notification-service | Scale Celery workers | Email provider rate limits |

### 9.2 Caching Strategy

| Cache | Key Pattern | TTL | Invalidation |
|-------|------------|-----|--------------|
| Course metadata | `course:{id}:meta` | 5 min | On publish, on edit |
| Catalog page | `catalog:page:{hash}` | 2 min | Time-based |
| User profile | `user:{id}:profile` | 10 min | On update |
| Enrollment check | `enrolled:{user_id}:{course_id}` | 15 min | On enrollment change |
| AI response | `ai:cache:{query_hash}:{course_id}:{version_id}` | 1 hour | On new version |
| Rate limit | `ratelimit:{user_id}:{endpoint}` | Sliding window | Auto-expire |

## 10. Failure Modes & Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| PostgreSQL down | All writes fail | Automatic failover (if HA configured), services return 503 |
| Kafka down | Events not published | Outbox accumulates; relay catches up on recovery |
| Qdrant down | Search/AI degraded | AI returns error; catalog falls back to PostgreSQL keyword search |
| Temporal down | Publishing stalls | Workflows resume automatically on Temporal recovery |
| LLM provider down | AI features unavailable | Graceful degradation: show error, log, platform still functional |
| Redis down | Cache miss, rate limits fail | Services function (slower); rate limiting falls back to permissive |
| MinIO down | Asset uploads/downloads fail | Upload returns error; downloads from CDN cache if available |

## 11. Directory Structure (Monorepo)

```
educorp/
├── prd.md                          # Product Requirements Document
├── apps/
│   └── web/                        # First-party frontend (React + Vite)
│       ├── src/
│       │   ├── app/                # Router, providers, app shell
│       │   ├── features/           # Route-scoped UI modules
│       │   ├── components/         # Shared UI building blocks
│       │   ├── lib/                # API client, auth/session helpers
│       │   └── styles/             # Design tokens and global CSS
│       ├── public/
│       ├── package.json
│       └── vite.config.ts
├── docs/                           # Project documentation
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACTS.md
│   ├── FRONTEND.md
│   ├── DATA_MODELS.md
│   ├── INFRASTRUCTURE.md
│   ├── SECURITY.md
│   ├── AI_SYSTEM.md
│   ├── OBSERVABILITY.md
│   ├── TESTING_STRATEGY.md
│   └── PHASES.md
├── .github/
│   ├── copilot-instructions.md     # Workspace-wide AI coding instructions
│   ├── agents/                     # Custom Copilot agents
│   └── instructions/               # File-specific Copilot instructions
├── services/
│   ├── auth/                       # Auth service
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py             # FastAPI app factory
│   │   │   ├── config.py           # Pydantic Settings
│   │   │   ├── dependencies.py     # DI (DB sessions, auth)
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── __init__.py
│   │   │   │       └── routes/     # Route modules
│   │   │   ├── models/             # SQLAlchemy models
│   │   │   ├── schemas/            # Pydantic request/response
│   │   │   ├── services/           # Business logic
│   │   │   ├── repositories/       # Data access
│   │   │   └── events/             # Outbox event helpers
│   │   ├── alembic/                # Migrations
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── course/                     # Same structure
│   ├── enrollment/
│   ├── progress/
│   ├── publishing/
│   │   └── app/
│   │       ├── workflows/          # Temporal workflow definitions
│   │       ├── activities/         # Temporal activity implementations
│   │       └── worker.py           # Temporal worker entrypoint
│   ├── ai/
│   │   └── app/
│   │       ├── chains/             # LangChain/LangGraph chains
│   │       ├── retrievers/         # Qdrant retrieval logic
│   │       └── tools/              # LangChain tools
│   ├── search/
│   ├── notification/
│   │   └── app/
│   │       ├── tasks/              # Celery tasks
│   │       └── celery_app.py       # Celery configuration
│   └── analytics/
├── shared/
│   ├── educorp_common/         # Shared Python package
│   │   ├── __init__.py
│   │   ├── auth/                   # JWT validation, RBAC decorators
│   │   ├── events/                 # Event schemas, outbox helpers
│   │   ├── config/                 # Base config, env helpers
│   │   ├── database/               # DB setup, base models
│   │   ├── middleware/             # Correlation ID, logging
│   │   ├── schemas/               # Shared Pydantic schemas
│   │   └── telemetry/             # OpenTelemetry setup
│   └── pyproject.toml
├── infra/
│   ├── docker/                     # Service Dockerfiles (if shared)
│   ├── kafka/
│   │   ├── topics.sh               # Topic creation script
│   │   └── schemas/                # JSON Schema files
│   ├── temporal/
│   │   └── init.sh                 # Namespace setup
│   ├── postgres/
│   │   └── init.sql                # Schema creation
│   ├── monitoring/
│   │   ├── prometheus/
│   │   │   └── prometheus.yml
│   │   ├── grafana/
│   │   │   ├── provisioning/
│   │   │   └── dashboards/
│   │   └── jaeger/
│   └── traefik/
│       ├── traefik.yml
│       └── dynamic/
├── scripts/
│   ├── dev-setup.sh                # One-command dev setup (cross-platform)
│   ├── seed-data.sh                # Seed development data
│   └── run-tests.sh                # Run all tests
├── docker-compose.yml              # Full development stack
├── docker-compose.infra.yml        # Infrastructure only (for running services locally)
├── Makefile                        # Developer shortcuts
├── pyproject.toml                  # Root workspace config
├── .env.example                    # Environment variable template
└── README.md                       # Getting started
```
