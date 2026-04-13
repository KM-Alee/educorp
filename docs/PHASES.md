# EduCorp — Development Phases

## Overview

The project is divided into 8 phases (Phase 0–7). Each phase produces a **testable increment** — something you can manually verify end-to-end before moving on. Phases are sequential; each builds on the previous.

Frontend work is not deferred until the backend is complete. Starting in Phase 0, each phase includes a backend track and a first-party web track so product flows can be exercised through the UI as the APIs land.

```
Phase 0: Scaffolding & Infrastructure Bootstrap
Phase 1: Authentication & User Management
Phase 2: Course Authoring & Content Management
Phase 3: Publishing Pipeline & Search
Phase 4: Enrollment & Progress Tracking
Phase 5: AI Assistant & Instructor Tools
Phase 6: Notifications & Analytics
Phase 7: Observability, Hardening & Production Readiness
```

---

## Phase 0 — Scaffolding & Infrastructure Bootstrap

> **Goal**: Every piece of infrastructure runs. Every service skeleton starts, connects to its dependencies, and responds on its health endpoint. Development workflow is smooth on both Linux and Windows.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Monorepo structure** | Full directory tree as specified in ARCHITECTURE.md §11 |
| **Docker Compose** | All 20+ containers defined, configured, and healthy |
| **Service skeletons** | 9 FastAPI services with `main.py`, health endpoints, config loading |
| **Shared library** | `educorp_common` package with base config, DB setup, middleware stubs |
| **Database init** | PostgreSQL schema creation, Alembic setup per service |
| **Kafka** | Topics created, schema registry running |
| **Temporal** | Namespace created, worker skeleton |
| **MinIO** | Bucket created (`course-assets`) |
| **Monitoring** | Prometheus scraping health endpoints, Grafana accessible |
| **Dev tooling** | Makefile, `.env.example`, dev-setup script, `.gitattributes`, `pyproject.toml` |
| **Traefik** | Routing to all services, CORS configured |
| **Frontend foundation** | `apps/web` scaffold, router, API client, auth/session primitives, shared design tokens |

### Tasks

1. **Create monorepo directory structure**
   - `services/` with all 9 service directories
   - `shared/educorp_common/` package
   - `infra/` with all infrastructure configs
   - `docs/`, `scripts/`, root configs

2. **Set up Python workspace**
   - Root `pyproject.toml` with workspace config, ruff, mypy settings
   - Per-service `pyproject.toml` with dependencies
   - Shared library as installable package (`pip install -e shared/`)
   - Use `uv` as package manager for speed

3. **Create shared library (`educorp_common`)**
   - `config/base.py` — Pydantic BaseSettings with common env vars
   - `database/session.py` — SQLAlchemy async engine + session factory
   - `database/base.py` — Declarative base with common mixins (timestamps, UUID PK)
   - `middleware/correlation.py` — Correlation ID middleware (stub)
   - `middleware/logging.py` — Structlog setup (stub)
   - `schemas/responses.py` — Standard response envelope (success, error, paginated)
   - `auth/dependencies.py` — JWT validation dependency (stub, returns mock user for now)

4. **Create service skeletons (for each of 9 services)**
   - `app/main.py` — FastAPI app factory with lifespan, health endpoints
   - `app/config.py` — Service-specific Pydantic Settings extending base
   - `app/dependencies.py` — DB session, Redis, auth dependency injection
   - `app/api/v1/__init__.py` — API router stub
   - `Dockerfile` — Multi-stage build (or use shared Dockerfile with build args)
   - `alembic.ini` + `alembic/env.py` — Migration setup (auth, course, enrollment, progress, publishing, notification, analytics)
   - `tests/conftest.py` — Test fixture setup (DB, client)

5. **Docker Compose configuration**
   - `docker-compose.yml` with all infrastructure + service containers
   - `docker-compose.infra.yml` with infrastructure only (for local dev)
   - Volume mounts for hot-reload during development
   - Health checks on all containers
   - Dependency ordering (services wait for DBs, Kafka, etc.)

6. **Infrastructure initialization scripts**
   - `infra/postgres/init.sql` — Schema creation
   - `infra/kafka/topics.sh` — Topic creation
   - `infra/temporal/init.sh` — Namespace setup
   - MinIO bucket creation (via docker-compose command)

7. **Traefik gateway configuration**
   - Static config (`traefik.yml`)
   - Dynamic routing rules (path → service mapping)
   - CORS middleware

8. **Monitoring baseline**
   - `infra/monitoring/prometheus/prometheus.yml` — Scrape all service `/metrics`
   - Grafana with provisioned Prometheus data source
   - Jaeger receiving OTLP

9. **Developer experience**
   - `Makefile` with common commands
   - `.env.example` with all variables documented
   - `.gitattributes` for cross-platform line endings
   - `.gitignore` covering Python, Docker, IDE files
   - `scripts/dev-setup.sh` — One-command setup: copy `.env`, build, up, wait for health, create topics
   - `README.md` — Getting started guide

10. **Create frontend foundation**
  - `apps/web/` with Vite + TypeScript application scaffold
  - Global design tokens and CSS variables for the warm editorial UI system
  - Shared API client pointed at Traefik (`/api/v1/*`)
  - Router, query client, and session storage primitives
  - Test harness for component and route-level tests

### Testable Outcome

```bash
# After running:
make up

# Verify these manually:
# 1. All containers are running
docker compose ps  # All healthy

# 2. Health endpoints respond
curl http://localhost/api/v1/auth/health/ready     # → {"status": "ready"}
curl http://localhost/api/v1/courses/health/ready   # → {"status": "ready"}
# ... (all 9 services)

# 3. Infrastructure UIs are accessible
# Grafana:    http://localhost:3000 (admin/admin)
# Temporal:   http://localhost:8088
# RabbitMQ:   http://localhost:15672 (educorp/educorp_dev)
# MinIO:      http://localhost:9001 (educorp/educorp_dev)
# Jaeger:     http://localhost:16686
# Traefik:    http://localhost:8081

# 4. Database schemas exist
docker compose exec postgres psql -U educorp -c "\dn"
# → auth, course, enrollment, progress, publishing, notification, analytics

# 5. Kafka topics exist
make kafka-list
# → user.lifecycle, course.lifecycle, enrollment.lifecycle, ...

# 6. Alembic migrations run
make migrate
# → All services migrated successfully
```

### Exit Criteria
- [ ] `docker compose up -d` brings up all containers to healthy state
- [ ] All 9 service health endpoints return 200 via Traefik
- [ ] PostgreSQL has all schemas created
- [ ] Kafka has all topics
- [ ] Temporal namespace `educorp` exists
- [ ] MinIO bucket `course-assets` exists
- [ ] Grafana loads with Prometheus data source
- [ ] Alembic migrations run without errors
- [ ] Works on both Linux and Windows (Docker Desktop)
- [ ] `apps/web` starts locally and can reach the gateway APIs

---

## Phase 1 — Authentication & User Management

> **Goal**: Users can register, verify email, login, get JWT tokens, refresh tokens, and access role-protected endpoints. Admins can manage users and roles.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **User registration** | POST `/auth/register` with validation, hashing, role assignment |
| **Email verification** | POST `/auth/verify-email` (mock email sender for now) |
| **Login** | POST `/auth/login` returning access + refresh tokens |
| **Token refresh** | POST `/auth/refresh` with rotation |
| **Password reset** | POST `/auth/forgot-password`, POST `/auth/reset-password` |
| **Profile** | GET/PATCH `/auth/me` |
| **RBAC middleware** | `require_roles()` dependency, role checking |
| **JWT validation** | Shared library: token creation, validation, revocation |
| **Admin user management** | GET users, PATCH roles, activate/deactivate users |
| **Instructor applications** | POST apply, GET/PATCH review (admin) |
| **Audit logging** | All auth actions logged to audit_log table |
| **Event emission** | UserCreated, RoleChanged events to outbox |
| **Seed script** | Create admin user, sample students/instructors |
| **Tests** | Unit tests for hashing/JWT, integration tests for all endpoints |
| **Auth web flows** | Register, login, verify email, forgot/reset password, profile UI |
| **Session shell** | Protected app shell with token refresh and role-aware navigation |
| **Admin console (initial)** | User list, role update, activation toggle, instructor application review |
| **Design system slice** | Warm editorial auth/admin interface adapted from the Cursor brief for product use |

### Tasks

1. **Implement SQLAlchemy models** — `users`, `roles`, `user_roles`, `refresh_tokens`, `password_resets`, `email_verifications`, `instructor_applications`, `audit_log`
2. **Create Alembic migration** for all auth tables
3. **Implement password hashing** — Argon2id via passlib
4. **Implement JWT utilities** — Create/validate access tokens, create/validate/rotate refresh tokens
5. **Implement registration endpoint** — Validate input, hash password, assign student role, create verification token, emit event
6. **Implement login endpoint** — Validate credentials, check active/verified, generate tokens
7. **Implement token refresh** — Validate refresh token, rotate (invalidate old, create new pair)
8. **Implement email verification** — Verify token, activate account
9. **Implement password reset** — Request (generate token), reset (validate + update)
10. **Implement profile endpoints** — GET `/me`, PATCH `/me`
11. **Implement RBAC dependency** — `require_roles("admin")` etc.
12. **Implement admin endpoints** — List users, change roles, activate/deactivate
13. **Implement instructor applications** — Apply, list pending, approve/reject
14. **Implement audit logging** — Middleware or explicit calls for all auth actions
15. **Implement outbox writes** — UserCreated, RoleChanged events
16. **Write seed script** — Admin user, test students/instructors
17. **Write tests** — Unit (password, JWT), integration (all endpoints)
18. **Build Phase 1 frontend routes** — `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`, `/app/profile`
19. **Build admin frontend routes** — `/app/admin/users`, `/app/admin/instructor-applications`
20. **Implement frontend session handling** — access token storage, refresh rotation, auth guards, role guards
21. **Implement frontend form UX** — validation, API error states, optimistic updates only where safe
22. **Write frontend tests** — auth form, route guard, API client, and admin screen coverage

### Testable Outcome

```bash
# 1. Register a new user
curl -X POST http://localhost/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"TestPass123!","first_name":"Jane","last_name":"Doe"}'
# → 201: user object with roles=["student"]

# 2. Login
curl -X POST http://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"TestPass123!"}'
# → 200: {access_token, refresh_token, expires_in}

# 3. Access protected endpoint
curl http://localhost/api/v1/auth/me \
  -H 'Authorization: Bearer <access_token>'
# → 200: user profile

# 4. Refresh token
curl -X POST http://localhost/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_token>"}'
# → 200: new token pair

# 5. Role-protected endpoint rejects unauthorized
curl http://localhost/api/v1/admin/users \
  -H 'Authorization: Bearer <student_token>'
# → 403: Forbidden

# 6. Admin can manage users
curl http://localhost/api/v1/admin/users \
  -H 'Authorization: Bearer <admin_token>'
# → 200: user list

# 7. Audit log populated
docker compose exec postgres psql -U educorp -c "SELECT action, resource_type FROM auth.audit_log LIMIT 5;"
# → Shows auth actions

# 8. Web app auth flow works
# Open http://localhost:5173
# - Register user
# - Verify email with token from mock flow
# - Login and land on profile screen
# - Admin can review users and instructor applications
```

### Exit Criteria
- [ ] Full registration → login → protected access flow works
- [ ] JWT tokens validate correctly; expired tokens rejected
- [ ] Token refresh with rotation works
- [ ] RBAC: student can't access admin endpoints; admin can
- [ ] Password reset flow works (mock email)
- [ ] Admin can list users, change roles, approve/reject instructor apps
- [ ] Audit log records all auth actions
- [ ] Outbox has UserCreated events
- [ ] All tests pass with >80% coverage on auth service
- [ ] Phase 1 web screens work against the live auth APIs
- [ ] Admin-only screens are hidden from non-admin users and rejected server-side if forced

### Frontend Notes

- The UI direction is intentionally restrained: warm cream surfaces, dark brown text, expressive but readable typography, and minimal motion.
- Use the Cursor brief as a structural reference only. Adapt it for a real product shell, not a landing page.
- Prefer durable interaction patterns over decorative effects. No hero gradients, glow halos, or generic AI visuals.

---

## Phase 2 — Course Authoring & Content Management

> **Goal**: Instructors can create courses, add/reorder modules, upload assets to MinIO, and validate drafts. Content stored in PostgreSQL (structure) and MongoDB (rich content).

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Course CRUD** | Create, read, update, soft-delete courses |
| **Module CRUD** | Add, edit, reorder, delete modules within a course |
| **Asset upload** | Multipart file upload to MinIO |
| **Asset management** | List, delete, download (presigned URL) |
| **Draft validation** | Pre-publish validation (metadata, modules, assets) |
| **MongoDB integration** | Rich content storage for drafts |
| **Authorization** | Instructor owns courses; admin can access all |
| **Catalog stub** | List READY courses (no READY courses yet, but endpoint works) |
| **Tests** | CRUD tests, upload tests, validation tests |

### Tasks

1. **Implement SQLAlchemy models** — `courses`, `modules`, `assets`
2. **Create Alembic migration** for course tables
3. **Set up MongoDB connection** — Motor async driver, collection access
4. **Implement MinIO client** — Upload, presigned download, delete
5. **Implement course endpoints** — POST, GET (single + list), PATCH, DELETE
6. **Implement module endpoints** — POST, GET list, PATCH, DELETE, reorder
7. **Implement asset upload** — File validation (type, size, magic bytes), upload to MinIO, create DB record
8. **Implement asset download** — Generate presigned URL
9. **Implement draft validation** — Check required fields, at least 1 module, valid asset types
10. **Implement slug generation** — Auto-generate unique slug from title
11. **Implement course ownership checks** — Only instructor-owner or admin can edit
12. **Write tests** — CRUD operations, file upload, validation errors

### Testable Outcome

```bash
# 1. Create a course (as instructor)
curl -X POST http://localhost/api/v1/courses \
  -H 'Authorization: Bearer <instructor_token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Intro to ML","description":"Learn ML basics","category":"CS","difficulty":"beginner"}'
# → 201: course with DRAFT visibility

# 2. Add a module
curl -X POST http://localhost/api/v1/courses/<course_id>/modules \
  -H 'Authorization: Bearer <instructor_token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"What is ML?","sort_order":0}'
# → 201: module

# 3. Upload an asset (PDF)
curl -X POST http://localhost/api/v1/courses/<course_id>/modules/<module_id>/assets/upload \
  -H 'Authorization: Bearer <instructor_token>' \
  -F 'file=@lecture-notes.pdf' \
  -F 'title=Lecture 1 Notes'
# → 201: asset with storage_path

# 4. List course with modules and assets
curl http://localhost/api/v1/courses/<course_id> \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: course with modules[].asset_count

# 5. Download asset (presigned URL)
curl http://localhost/api/v1/courses/<course_id>/modules/<module_id>/assets/<asset_id>/download \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: {download_url: "https://...presigned..."}

# 6. Validate draft (should fail — add validation issues)
# Validation runs as part of publish preparation (Phase 3)

# 7. Verify MinIO has the file
# MinIO UI: http://localhost:9001 → Browse course-assets bucket
```

### Exit Criteria
- [ ] Instructor can create course → add modules → upload assets → see full course
- [ ] Non-owner instructor/student cannot edit the course (403)
- [ ] File upload validates type, size, stores in MinIO
- [ ] Presigned download URL works
- [ ] Module reordering works
- [ ] Soft-delete works for courses
- [ ] MongoDB stores rich draft content
- [ ] All tests pass with >80% coverage on course service

---

## Phase 3 — Publishing Pipeline & Search

> **Goal**: Instructor hits "Publish", a Temporal workflow extracts text, chunks content, generates embeddings, indexes for search, and marks the version READY. Students can search and browse the course catalog.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Course versioning** | `course_versions` table, version state machine |
| **Publish endpoint** | POST `/courses/{id}/publish` → creates version, starts workflow |
| **Temporal workflow** | `PublishCourseWorkflow` with 5 activities |
| **Text extraction** | PDF, DOCX, PPTX, TXT, VTT/SRT extractors |
| **Chunking** | Recursive text splitting with metadata |
| **Embedding generation** | OpenAI-compatible embedding API calls |
| **Qdrant indexing** | Store chunks with embeddings and metadata |
| **Publishing status API** | GET version status with per-step progress |
| **Catalog browse** | GET courses with filters (only READY) |
| **Keyword search** | Search by title/description |
| **Outbox + relay** | Transactional outbox for CourseReady/CoursePublishFailed events |
| **Version management** | Retry failed, cancel in-progress |
| **Tests** | Workflow tests (mocked extractors), search tests |

### Tasks

1. **Implement `course_versions` and `publishing_steps` models** + migration
2. **Implement `chunks` table** + migration
3. **Set up Temporal worker** in publishing service
4. **Implement Temporal activities**:
   - `ValidateAssetsActivity` — Check all assets exist in MinIO
   - `ExtractTextActivity` — Extract text from each asset
   - `ChunkContentActivity` — Split into chunks with metadata
   - `GenerateEmbeddingsActivity` — Call embedding API in batches
   - `IndexInQdrantActivity` — Upsert chunks + embeddings to Qdrant
   - `FinalizeVersionActivity` — Mark READY, update course.current_version_id, emit event
5. **Implement `PublishCourseWorkflow`** — Orchestrate activities with error handling
6. **Implement publish endpoint** — Validate draft, create version, start workflow
7. **Implement status endpoint** — Query Temporal + publishing_steps for progress
8. **Implement retry/cancel endpoints**
9. **Set up text extractors** — pdfplumber, python-docx, python-pptx, webvtt-py
10. **Set up Qdrant collection** — Create with proper vector config and payload indexes
11. **Implement catalog browse** — Query courses WHERE visibility='PUBLISHED' AND current_version.status='READY'
12. **Implement keyword search** — PostgreSQL full-text search on title + description
13. **Implement outbox relay** — Poll outbox → publish to Kafka (or Debezium CDC)
14. **Write tests** — Workflow end-to-end (with mocked LLM), extractor unit tests, search tests

### Testable Outcome

```bash
# Setup: Create a course with modules and assets (from Phase 2)

# 1. Publish the course
curl -X POST http://localhost/api/v1/courses/<course_id>/publish \
  -H 'Authorization: Bearer <instructor_token>'
# → 202: {version_id, status: "PUBLISHING", workflow_id}

# 2. Monitor publishing status
curl http://localhost/api/v1/publishing/versions/<version_id> \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: steps with COMPLETED/RUNNING/PENDING statuses

# 3. Wait for completion (monitor Temporal UI at http://localhost:8088)

# 4. Verify version is READY
curl http://localhost/api/v1/publishing/versions/<version_id> \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: {status: "READY", total_chunks: N}

# 5. Course appears in catalog
curl http://localhost/api/v1/courses
# → 200: course listed with current_version.status = "READY"

# 6. Search works
curl "http://localhost/api/v1/search/courses?q=machine+learning"
# → 200: course in results

# 7. Qdrant has chunks
curl http://localhost:6333/collections/course_chunks
# → Collection with N points

# 8. Kafka has events
# Check Kafka topic for CourseReady event
```

### Exit Criteria
- [ ] Publish creates version, starts Temporal workflow, processes through all steps
- [ ] Text extraction works for PDF, DOCX, PPTX, TXT
- [ ] Chunks stored in both PostgreSQL (reference) and Qdrant (vectors)
- [ ] Embeddings generated via LLM provider
- [ ] Version transitions: PUBLISHING → READY or PUBLISHING → FAILED
- [ ] Failed publish doesn't affect previous READY version
- [ ] Course appears in catalog and search only when READY
- [ ] Temporal UI shows workflow history
- [ ] Retry failed workflow works
- [ ] All tests pass

---

## Phase 4 — Enrollment & Progress Tracking

> **Goal**: Students can enroll in courses (with prerequisite checks and capacity enforcement), track module-level progress, complete courses, and receive certificates.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Enrollment API** | POST `/enrollments` — idempotent, capacity-safe |
| **Prerequisite checks** | Verify completed prerequisite courses |
| **Capacity enforcement** | Concurrent-safe capacity limits via distributed lock |
| **Enrollment status** | GET enrollment details, check enrollment |
| **Progress initialization** | Create progress records on enrollment |
| **Module completion** | POST mark module complete |
| **Course completion** | Auto-detect, emit event, generate certificate |
| **Student dashboard** | GET progress dashboard |
| **Certificate issuance** | Certificate record on completion |
| **Outbox events** | EnrollmentCreated, CourseCompleted |
| **Tests** | Concurrency tests, idempotency tests, progress tests |

### Tasks

1. **Implement enrollment models** — `enrollments`, `enrollment_audit` + migration
2. **Implement progress models** — `student_progress`, `module_progress`, `certificates` + migration
3. **Implement enrollment endpoint** — Idempotency key, prerequisite check, capacity check (Redis lock), create enrollment, initialize progress
4. **Implement prerequisite checking** — Query completed enrollments for prerequisite courses
5. **Implement capacity enforcement** — Redis distributed lock + count query in same transaction
6. **Implement enrollment status** — GET `/enrollments`, GET enrollment detail, enrollment check
7. **Implement cancel enrollment**
8. **Implement progress initialization** — Create module_progress rows for all required modules on enrollment
9. **Implement module completion** — Mark module complete, recalculate overall progress
10. **Implement course completion detection** — When all required modules complete: mark complete, generate certificate, emit event
11. **Implement certificate generation** — Unique certificate number, store in DB
12. **Implement student dashboard** — Aggregate progress across enrollments
13. **Implement certificate endpoints** — List, view detail (public for verification)
14. **Write events to outbox** — EnrollmentCreated, CourseCompleted
15. **Write tests** — Concurrency (capacity), idempotency, prerequisite, completion flow

### Testable Outcome

```bash
# Setup: Have a READY course from Phase 3

# 1. Enroll in course
curl -X POST http://localhost/api/v1/enrollments \
  -H 'Authorization: Bearer <student_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>"}'
# → 201: enrollment with status=ENROLLED

# 2. Duplicate enrollment returns same result (idempotent)
curl -X POST http://localhost/api/v1/enrollments \
  -H 'Authorization: Bearer <student_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>"}'
# → Returns existing enrollment

# 3. View progress (should show 0%)
curl http://localhost/api/v1/progress/enrollments/<enrollment_id> \
  -H 'Authorization: Bearer <student_token>'
# → 200: progress_percent=0, modules with is_completed=false

# 4. Complete first module
curl -X POST http://localhost/api/v1/progress/enrollments/<enrollment_id>/modules/<module_id>/complete \
  -H 'Authorization: Bearer <student_token>'
# → 200: {is_completed: true, overall_progress_percent: 50.0}

# 5. Complete all modules → course completion + certificate
curl -X POST http://localhost/api/v1/progress/enrollments/<enrollment_id>/modules/<last_module_id>/complete \
  -H 'Authorization: Bearer <student_token>'
# → 200: {course_completed: true, certificate: {id, certificate_number}}

# 6. View dashboard
curl http://localhost/api/v1/progress/dashboard \
  -H 'Authorization: Bearer <student_token>'
# → 200: {completed_courses: 1, certificates: 1}

# 7. Verify certificate (public)
curl http://localhost/api/v1/progress/certificates/<cert_id>
# → 200: certificate details

# 8. Capacity test (if course has max_capacity=1, second enrollment fails)
```

### Exit Criteria
- [ ] Enrollment is idempotent (same student + course = same enrollment)
- [ ] Capacity enforced under concurrent enrollments (test with parallel requests)
- [ ] Prerequisites checked before enrollment
- [ ] Progress initialized on enrollment
- [ ] Module completion updates overall progress
- [ ] Course completion triggers certificate generation
- [ ] Certificate Number is unique and verifiable
- [ ] Dashboard shows aggregated progress
- [ ] Outbox has EnrollmentCreated and CourseCompleted events
- [ ] All tests pass including concurrency tests

---

## Phase 5 — AI Assistant & Instructor Tools

> **Goal**: Enrolled students can ask questions about course content and receive cited answers (streamed via SSE). Instructors can generate summaries, quizzes, and learning objectives from course material.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Q&A endpoint** | POST `/ai/ask` — non-streaming answer with citations |
| **SSE streaming** | GET `/ai/ask/stream` — streaming tokens + citations |
| **LangGraph state machine** | Validate → Retrieve → Assess → Generate/Refuse/Clarify → Cite → Log |
| **Qdrant retrieval** | Semantic search scoped to course + READY version |
| **Citation builder** | Extract and validate reference numbers from answer |
| **Refusal behavior** | Refuse when <2 relevant chunks or low scores |
| **Entitlement check** | Verify enrollment before allowing Q&A |
| **Rate limiting** | Redis sliding window for AI endpoints |
| **Response caching** | Cache repeated questions per course version |
| **Instructor enhancement** | POST `/ai/instructor/enhance` — async jobs (summary, objectives, quiz, glossary) |
| **Streaming enhancement** | GET `/ai/instructor/enhance/stream` — interactive mode |
| **Job management** | GET job status, cancel job, list jobs |
| **AI event logging** | AssistantQueryAsked event to Kafka |
| **Tests** | RAG tests with mocked LLM, refusal tests, streaming tests |

### Tasks

1. **Set up LangChain/LangGraph** in ai-service
2. **Implement LLM client wrapper** — OpenAI-compatible, with error handling and metrics
3. **Implement embedding client** — For query embedding
4. **Implement Qdrant retriever** — Search with course_id + version_status filters
5. **Build LangGraph Q&A state machine** — All nodes as described in AI_SYSTEM.md
6. **Implement SSE streaming endpoint** — `sse-starlette` for token streaming
7. **Implement citation builder** — Parse `[n]` references, validate against chunks
8. **Implement refusal/clarification logic** — Threshold-based routing
9. **Implement entitlement check middleware** — Verify enrollment for AI access
10. **Implement AI rate limiting** — Redis sliding window (20 req/min per user)
11. **Implement response caching** — Redis cache with question hash + course + version
12. **Implement instructor enhancement chains** — Summary, objectives, quiz, glossary prompts
13. **Implement async job system** — In-memory job queue (or Celery/Redis-backed)
14. **Implement job management endpoints** — Status, cancel, list
15. **Implement streaming enhancement** — SSE for interactive instructor use
16. **Implement AI event emission** — Log to Kafka via outbox or direct produce
17. **Write tests** — Mocked LLM, retrieval tests, citation validation, streaming tests

### Testable Outcome

```bash
# Setup: Have a READY course with enrolled student

# 1. Ask a question (non-streaming)
curl -X POST http://localhost/api/v1/ai/ask \
  -H 'Authorization: Bearer <enrolled_student_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>","question":"What is machine learning?"}'
# → 200: {answer: "...", citations: [{chunk_id, module_title, asset_title, text_snippet}]}

# 2. Stream a question (SSE)
curl -N http://localhost/api/v1/ai/ask/stream?course_id=<id>&question=What+is+ML \
  -H 'Authorization: Bearer <enrolled_student_token>'
# → SSE stream: event:token, event:token, ..., event:citation, event:done

# 3. Ask irrelevant question → refusal
curl -X POST http://localhost/api/v1/ai/ask \
  -H 'Authorization: Bearer <enrolled_student_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>","question":"What is the capital of France?"}'
# → 200: {answer: "Not enough information in course materials...", citations: []}

# 4. Unenrolled student → forbidden
curl -X POST http://localhost/api/v1/ai/ask \
  -H 'Authorization: Bearer <unenrolled_student_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>","question":"Test?"}'
# → 403

# 5. Instructor tool: Generate quiz
curl -X POST http://localhost/api/v1/ai/instructor/enhance \
  -H 'Authorization: Bearer <instructor_token>' \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"<course_id>","job_type":"quiz","scope":"module","module_id":"<module_id>"}'
# → 202: {job_id, status: "QUEUED"}

# 6. Poll job
curl http://localhost/api/v1/ai/instructor/jobs/<job_id> \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: {status: "COMPLETED", result: {questions: [...]}}

# 7. Rate limiting works (make >20 requests/min)
# → 429 after limit reached
```

### Exit Criteria
- [ ] Q&A returns answers with valid citations referencing actual course chunks
- [ ] SSE streaming delivers tokens in real-time
- [ ] Refusal works for irrelevant/out-of-scope questions
- [ ] Only enrolled students can use Q&A (entitlement check)
- [ ] Rate limiting enforced (20 req/min for AI)
- [ ] Cached responses served for repeated questions
- [ ] Instructor can generate summaries, quizzes, objectives
- [ ] Job lifecycle visible (queued → running → completed/failed)
- [ ] AI events logged to Kafka
- [ ] All tests pass with mocked LLM

---

## Phase 6 — Notifications & Analytics

> **Goal**: Users receive notifications for key events (enrollment, completion, publishing). Platform and course analytics are collected from Kafka events and displayed via API.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **Notification service** | Celery workers for email + in-app notifications |
| **Kafka consumers** | notification-service consumes events, triggers notifications |
| **In-app notifications** | Store, list (unread/all), mark read |
| **Email notifications** | Template-based email sending (SMTP or mock) |
| **Notification preferences** | Per-user preferences for notification types |
| **Analytics consumers** | analytics-service consumes all domain events |
| **Event store** | Immutable event log in analytics schema |
| **Aggregation** | Daily metrics computation, course metrics |
| **Platform analytics API** | Admin dashboard data |
| **Course analytics API** | Instructor course metrics |
| **Outbox relay** | Ensure all outbox events reach Kafka topics |
| **Tests** | Consumer tests, aggregation tests |

### Tasks

1. **Set up Celery + RabbitMQ** in notification-service
2. **Implement Kafka consumers** in notification-service — Listen to `enrollment.lifecycle`, `course.lifecycle`, `progress.lifecycle`
3. **Implement notification routing** — Map event type → notification template → channel
4. **Implement in-app notification storage** — notifications table, CRUD endpoints
5. **Implement notification preferences** — Per-user settings
6. **Implement notification list/read endpoints** — GET list, PATCH read, POST read-all
7. **Implement email sending** — Celery task, SMTP (mock in dev, configurable)
8. **Implement Kafka consumers** in analytics-service — Consume all domain events
9. **Implement event store** — Write every consumed event to analytics.event_store
10. **Implement daily aggregation job** — Scheduled task to compute daily_metrics
11. **Implement course metrics materialization** — Keep course_metrics table updated
12. **Implement platform analytics endpoint** — Query aggregated data
13. **Implement course analytics endpoint** — Per-course metrics for instructors
14. **Implement outbox relay** — Polling relay that publishes unpublished outbox entries to Kafka
15. **Write tests** — Consumer event handling, aggregation logic, API tests

### Testable Outcome

```bash
# Setup: All previous phases working. Events flowing through the system.

# 1. Enroll → notification appears
curl -X POST http://localhost/api/v1/enrollments \
  -H 'Authorization: Bearer <student_token>' \
  -d '{"course_id":"<course_id>"}'
# → 201

# 2. Check notifications
curl http://localhost/api/v1/notifications \
  -H 'Authorization: Bearer <student_token>'
# → 200: [{type: "enrollment_confirmed", title: "You are enrolled in Intro to ML"}]

# 3. Complete course → certificate notification
# ... (mark all modules complete)

curl http://localhost/api/v1/notifications?is_read=false \
  -H 'Authorization: Bearer <student_token>'
# → 200: [{type: "course_completed", title: "Congratulations on completing..."}]

# 4. Mark notification read
curl -X PATCH http://localhost/api/v1/notifications/<notification_id>/read \
  -H 'Authorization: Bearer <student_token>'
# → 200

# 5. View platform analytics (admin)
curl http://localhost/api/v1/analytics/platform?from_date=2026-04-01&to_date=2026-04-11 \
  -H 'Authorization: Bearer <admin_token>'
# → 200: {total_students, enrollments, completions, ai_usage}

# 6. View course analytics (instructor)
curl http://localhost/api/v1/analytics/courses/<course_id> \
  -H 'Authorization: Bearer <instructor_token>'
# → 200: {total_enrollments, completion_rate, ai_queries}

# 7. Verify event store has events
docker compose exec postgres psql -U educorp -c \
  "SELECT event_type, COUNT(*) FROM analytics.event_store GROUP BY event_type;"
# → Shows event counts
```

### Exit Criteria
- [ ] Enrollment triggers in-app notification to student
- [ ] Course completion triggers notification to student
- [ ] Publishing success triggers notification to instructor
- [ ] Notification preferences respected
- [ ] Mark read / read all works
- [ ] Analytics event store captures all domain events
- [ ] Platform analytics endpoint returns metrics
- [ ] Course analytics endpoint returns instructor metrics
- [ ] Kafka consumers are stable and processing events
- [ ] All tests pass

---

## Phase 7 — Observability, Hardening & Production Readiness

> **Goal**: Full observability stack is wired up. Security hardened. Load-tested. Documentation complete. The system is production-ready.

### What Gets Built

| Component | Deliverable |
|-----------|-------------|
| **OpenTelemetry** | Full instrumentation across all services |
| **Prometheus metrics** | Custom business metrics exposed and scraped |
| **Grafana dashboards** | Platform overview, per-service, Kafka, AI, publishing dashboards |
| **Jaeger tracing** | Distributed traces across services + Kafka + Temporal |
| **Structured logging** | JSON logs with correlation IDs everywhere |
| **Alert rules** | Prometheus alerting rules for critical conditions |
| **Audit log consolidation** | Admin audit log API |
| **Admin ops console** | Workflow health, DLQ inspection, replay |
| **Rate limiting refinement** | Per-endpoint rate limits fully tuned |
| **Security headers** | All recommended security headers |
| **Load testing** | Locust tests for enrollment, catalog, AI endpoints |
| **Dependency audit** | pip-audit, no known vulnerabilities |
| **Documentation** | Final README, architecture diagrams, runbooks |
| **Error handling** | Consistent error responses, graceful degradation |

### Tasks

1. **Wire OpenTelemetry** into every service — Traces, metrics, context propagation
2. **Add custom Prometheus metrics** — Business metrics per service
3. **Create Grafana dashboards** — Platform overview, per-service, Kafka, AI
4. **Configure alert rules** — Error rate, latency, consumer lag, AI provider down
5. **Verify distributed tracing** — End-to-end trace from request → DB → Kafka → consumer
6. **Ensure structured logging** — All services emit JSON logs with correlation_id
7. **Implement admin audit log endpoint** — Searchable audit trail
8. **Implement admin ops endpoints** — Workflow list/retry, DLQ view/replay
9. **Add security headers** to all responses
10. **Tune rate limits** per endpoint based on expected traffic
11. **Run load tests** — Locust for enrollment, catalog browse, AI Q&A
12. **Run dependency audit** — `pip-audit` on all services
13. **Review and harden** — Input validation, SQL injection (verify ORM), file upload validation
14. **Test graceful degradation** — LLM down, Redis down, Kafka down
15. **Finalize documentation** — README, runbooks, architecture diagrams
16. **E2E test full journeys** — Journey A (publish), Journey B (enroll+learn), Journey C (AI Q&A)

### Testable Outcome

```bash
# 1. Grafana dashboards populated
# Visit http://localhost:3000
# → Platform Overview: request rate, error rate, latency graphs
# → AI Dashboard: query rate, token usage, cache hit rate
# → Kafka Dashboard: consumer lag, message rate

# 2. Jaeger shows distributed traces
# Visit http://localhost:16686
# → Search for service "auth-service" → see traces spanning DB queries
# → Search for "ai-service" → see trace spanning retrieval + LLM call

# 3. End-to-end journey works
# Journey A: Create course → upload assets → publish → READY in catalog
# Journey B: Browse → enroll → complete modules → certificate
# Journey C: Ask question → get cited answer with SSE stream

# 4. Graceful degradation
# Stop ai-service LLM mock → AI endpoint returns 502 with clear error
# Stop Redis → Services still function (slower, no cache, no rate limits)

# 5. Load test results
locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 5m
# → p95 enrollment < 500ms
# → p95 catalog browse < 300ms
# → p95 AI time-to-first-token < 2s

# 6. Security scan
pip-audit  # → No known vulnerabilities

# 7. Admin ops
curl http://localhost/api/v1/admin/workflows?status=FAILED \
  -H 'Authorization: Bearer <admin_token>'
# → List of failed workflows with error details

curl http://localhost/api/v1/admin/audit-log?action=ROLE_CHANGED \
  -H 'Authorization: Bearer <admin_token>'
# → Audit entries
```

### Exit Criteria
- [ ] Grafana dashboards show real-time metrics for all services
- [ ] Distributed traces visible in Jaeger for cross-service calls
- [ ] Structured JSON logs with correlation_id from all services
- [ ] Alert rules configured and firing on test triggers
- [ ] Admin can view workflow health, inspect DLQ, retry failed jobs
- [ ] Audit log is searchable and complete
- [ ] Load test meets NFR targets (p95 latency, throughput)
- [ ] No known vulnerabilities in dependencies
- [ ] All three user journeys (publish, learn, AI) work end-to-end
- [ ] Graceful degradation verified for LLM/Redis/Kafka outages
- [ ] Documentation complete (README, runbooks, architecture docs)

---

## Phase Summary

| Phase | Key Deliverable | Test Type | Duration Estimate |
|-------|----------------|-----------|-------------------|
| **0** | Infrastructure boots, health endpoints respond | Smoke test | Foundation |
| **1** | Register → login → protected access flow | Unit + integration | Core |
| **2** | Create course → upload assets | Unit + integration | Core |
| **3** | Publish → extract → chunk → embed → search | Integration + workflow | Complex |
| **4** | Enroll → progress → complete → certificate | Integration + concurrency | Complex |
| **5** | AI Q&A with citations + instructor tools | Integration + mock LLM | Complex |
| **6** | Notifications arrive, analytics populated | Integration + Kafka | Medium |
| **7** | Dashboards, tracing, load tests pass | E2E + load + security | Hardening |

### Dependencies Between Phases

```
Phase 0 ────► Phase 1 ────► Phase 2 ────► Phase 3 ────┐
                                                        │
                                          Phase 4 ◄─────┘
                                            │
                                          Phase 5
                                            │
                                          Phase 6
                                            │
                                          Phase 7
```

- Phase 3 depends on Phase 2 (needs courses + assets to publish)
- Phase 4 depends on Phase 3 (needs READY courses to enroll in)
- Phase 5 depends on Phase 4 (needs enrolled students to ask questions) and Phase 3 (needs chunks)
- Phase 6 depends on Phases 1-5 (consumes events from all services)
- Phase 7 depends on everything (hardening the full system)
