# Phase 4 Research Report

Date: 2026-04-16

## Objective

Research how Phase 4 should be implemented in this repository, based on the existing codebase, documented contracts, and established service patterns.

Phase 4 scope from `docs/PHASES.md`:

- Enrollment API with idempotency, prerequisites, and capacity enforcement
- Progress initialization on successful enrollment
- Module completion and overall progress tracking
- Course completion and certificate issuance
- Enrollment/progress outbox events
- Integration, idempotency, and concurrency testing

## Executive Summary

The repository is still at a skeleton state for the `enrollment` and `progress` services. The useful implementation evidence for Phase 4 is therefore in:

- shared service conventions in `shared/educorp_common`
- fully implemented patterns in `services/auth`
- cross-service HTTP client patterns in `services/course` and `services/publishing`
- data/API/test contracts in `docs/`

The main architectural constraint is already explicit in repository guidance: services must not query across schema boundaries. That means Phase 4 should not read `course.*` tables directly from `enrollment-service` or `progress-service`. It should use internal HTTP endpoints and/or events.

The main design tension is that Phase 4 requires immediate progress availability after enrollment, but enrollment and progress live in separate services and separate schemas. The safest repo-aligned approach is a hybrid:

1. `enrollment-service` performs authoritative enrollment checks and persistence.
2. `enrollment-service` calls `progress-service` synchronously to initialize progress for the new enrollment.
3. `enrollment-service` also writes an outbox event for reconciliation and downstream consumers.
4. `progress-service` makes its initialization idempotent so retries and replay are safe.

## Phase 4 Requirements Backed by Repo Docs

### Primary phase definition

`docs/PHASES.md` defines Phase 4 as:

- `POST /enrollments` with idempotency, prerequisite checks, and Redis-backed capacity enforcement
- progress initialization on enrollment
- `POST /progress/enrollments/{enrollment_id}/modules/{module_id}/complete`
- completion detection and certificate issuance
- dashboard and certificate APIs
- `EnrollmentCreated` and `CourseCompleted` events
- concurrency and idempotency tests

### API contract constraints

`docs/API_CONTRACTS.md` adds these concrete expectations:

- `POST /enrollments` returns `201`
- repeated enrollments can return the existing enrollment payload with `meta.idempotent_hit=true`
- `GET /courses/{course_id}/enrollment-status` returns enrollment state plus `progress_percent`
- progress detail returns module-level rows including `module_title`
- completing the final module returns certificate metadata inline
- certificate detail endpoint is public

### Data model constraints

`docs/DATA_MODELS.md` defines the canonical Phase 4 tables:

- `enrollment.enrollments`
- `enrollment.enrollment_audit`
- `progress.student_progress`
- `progress.module_progress`
- `progress.certificates`

It also documents Redis key patterns Phase 4 should reuse:

- `idempotency:{key}`
- `lock:enrollment:{course_id}`
- `cache:enrolled:{user_id}:{course_id}`

### Testing constraints

`docs/TESTING_STRATEGY.md` explicitly calls out:

- Phase 4 requires integration and concurrency tests
- capacity should be validated with parallel enrollment requests
- idempotent replays should return the original enrollment

## Current Codebase State

### Enrollment service

Current `services/enrollment` state is skeleton-only:

- `app/main.py` sets up FastAPI, DB engine, middleware, and router
- `app/dependencies.py` only exposes DB session and auth helpers
- `app/api/v1/__init__.py` only exposes health endpoints
- `models/`, `schemas/`, `repositories/`, and `services/` are empty
- tests currently only provide a minimal `AsyncClient` fixture

Implication: Phase 4 in `enrollment-service` is greenfield implementation within an existing service shell.

### Progress service

Current `services/progress` state is also skeleton-only:

- `app/main.py` mirrors the standard service factory pattern
- `app/dependencies.py` only exposes DB session and auth helpers
- domain folders are empty
- tests are only the minimal client fixture

Implication: all progress models, repositories, schemas, API routes, and services still need to be introduced.

### Shared conventions already implemented

The shared library already provides the conventions Phase 4 should follow:

- `shared/educorp_common/database/base.py`
  - `Base`
  - `UUIDPrimaryKeyMixin`
  - `TimestampMixin`
  - `SoftDeleteMixin`
- `shared/educorp_common/auth/dependencies.py`
  - JWT decoding to `CurrentUser`
  - `require_roles()` role guard factory
- `shared/educorp_common/schemas/responses.py`
  - `SuccessResponse`
  - `PaginatedResponse`
  - standard response metadata envelope
- `shared/educorp_common/errors.py`
  - `EduCorpError`
  - `ConflictError`, `ForbiddenError`, `NotFoundError`, `UnauthorizedError`, `ValidationError`

### Implemented service patterns to reuse

`services/auth` provides the clearest reference implementation for:

- repository pattern with `flush()` semantics
- service-layer orchestration
- transactional outbox writes
- audit logging repository/model pattern
- Redis wiring in dependencies

`services/course` and `services/publishing` provide the reference implementation for:

- service-to-service `httpx.AsyncClient` wrappers
- internal service auth via `X-Internal-Service-Token`
- correlation ID forwarding via `X-Correlation-Id`

## Context Map

### Files that are directly relevant

#### Enrollment service target area

- `services/enrollment/app/config.py`
- `services/enrollment/app/dependencies.py`
- `services/enrollment/app/api/v1/__init__.py`
- `services/enrollment/app/models/`
- `services/enrollment/app/schemas/`
- `services/enrollment/app/repositories/`
- `services/enrollment/app/services/`
- `services/enrollment/alembic/`
- `services/enrollment/tests/`

#### Progress service target area

- `services/progress/app/config.py`
- `services/progress/app/dependencies.py`
- `services/progress/app/api/v1/__init__.py`
- `services/progress/app/models/`
- `services/progress/app/schemas/`
- `services/progress/app/repositories/`
- `services/progress/app/services/`
- `services/progress/alembic/`
- `services/progress/tests/`

#### Reference implementations

- `shared/educorp_common/database/base.py`
- `shared/educorp_common/auth/dependencies.py`
- `shared/educorp_common/schemas/responses.py`
- `shared/educorp_common/errors.py`
- `services/auth/app/services/auth_service.py`
- `services/auth/app/repositories/outbox_repository.py`
- `services/auth/app/models/outbox.py`
- `services/auth/app/models/audit_log.py`
- `services/auth/app/repositories/audit_log_repository.py`
- `services/course/app/services/publishing_client.py`
- `services/publishing/app/services/course_activation_client.py`

#### Upstream dependencies for Phase 4 data

- `services/course/app/models/course.py`
- `services/course/app/models/module.py`
- `services/course/app/schemas/course.py`
- `services/course/app/services/course_service.py`
- `services/publishing/app/models/course_version.py`

#### Contract and planning docs

- `docs/PHASES.md`
- `docs/API_CONTRACTS.md`
- `docs/DATA_MODELS.md`
- `docs/TESTING_STRATEGY.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `prd.md`

## What Already Exists That Phase 4 Can Reuse

### 1. JWT/current-user handling

Use `educorp_common.auth.dependencies.get_current_user` and `require_roles()` as the baseline. Phase 4 endpoints can usually authorize by role first, then validate resource ownership in the service layer.

Recommended role posture:

- `POST /enrollments`: student only
- `GET /enrollments`: authenticated user, filtered to own enrollments unless admin
- `GET /progress/dashboard`: student only
- certificate verification detail: public

### 2. Error and envelope style

Use the existing error model rather than custom response shaping:

- `ConflictError` for already-enrolled, prerequisites-not-met, and course-full conditions
- `NotFoundError` for missing enrollment/progress/certificate
- `ForbiddenError` for cross-user access

All success responses should use the standard `data` + `meta` envelope.

### 3. Repository and service pattern

`services/auth` shows the intended structure:

- route handlers stay thin
- service layer coordinates business rules
- repositories handle persistence details
- repositories use `flush()`, not `commit()`

Phase 4 should follow that pattern in both services.

### 4. Transactional outbox pattern

`services/auth/app/repositories/outbox_repository.py` and `services/auth/app/models/outbox.py` provide the repo’s reference outbox shape.

Phase 4 should mirror that design in both services:

- `enrollment-service` emits enrollment lifecycle events
- `progress-service` emits progress lifecycle events

### 5. Service-to-service HTTP client pattern

There is already a concrete pattern for internal service clients:

- `services/course/app/services/publishing_client.py`
- `services/publishing/app/services/course_activation_client.py`

Those clients show the repo’s preferred behavior:

- use `httpx.AsyncClient`
- put URLs in service config
- forward correlation IDs
- pass internal auth headers for internal-only endpoints
- translate remote errors into `EduCorpError`

Phase 4 should reuse this pattern instead of inventing a new transport abstraction.

## Upstream Data Phase 4 Depends On

### Course metadata already present

`services/course/app/models/course.py` already contains the critical enrollment inputs:

- `max_capacity`
- `prerequisites`
- `visibility`
- `current_version_id`
- `title`

`services/course/app/models/module.py` already contains the critical progress inputs:

- `id`
- `title`
- `sort_order`
- `is_required`

### Publishing metadata already present

`services/publishing/app/models/course_version.py` already models publish readiness with `status`, including `READY`.

Implication: a Phase 4 enrollment decision should be based on course visibility/readiness exposed through `course-service`, not by direct database reads from `publishing-service` or `course-service` schemas.

## Architectural Constraints That Matter

### 1. Schema isolation is explicit repo policy

`AGENTS.md` says:

- never query across service schema boundaries
- use events or HTTP instead

This is the single most important design guardrail for Phase 4.

### 2. Enrollment correctness must hold under concurrency

The docs require both:

- a Redis distributed lock
- a DB uniqueness rule on `(student_id, course_id)`

Recommendation:

- use Redis lock for capacity race protection
- keep DB uniqueness as the final correctness guard for duplicate enrollment requests
- treat Redis as a coordination tool, not the sole source of truth

### 3. Immediate progress availability conflicts with strict event-only initialization

The phase outcome expects progress to be visible immediately after enrollment. An event-only model is eventually consistent and may miss that UX/API expectation.

Recommendation:

- use synchronous internal initialization from `enrollment-service` to `progress-service`
- still emit `EnrollmentCreated` for downstream consumers and reconciliation
- make the progress initialization endpoint idempotent

## Recommended Implementation Shape

### A. Enrollment-service owns authoritative enrollment decisions

Recommended responsibilities:

- authenticate the student
- fetch course enrollment context from `course-service`
- verify the course is enrollable
- verify prerequisites using the local enrollment database
- enforce capacity with Redis lock + DB count
- create the enrollment row
- create an audit row
- write an outbox event
- trigger progress initialization in `progress-service`

Recommended new internals:

- Redis wiring in `services/enrollment/app/dependencies.py`
- `EnrollmentService`
- `EnrollmentRepository`
- `EnrollmentAuditRepository`
- `OutboxRepository`
- internal `CourseClient`
- internal `ProgressClient`

### B. Progress-service owns learning state and certificates

Recommended responsibilities:

- idempotently initialize a `student_progress` row and `module_progress` rows
- return detailed progress state
- mark modules complete
- recalculate `progress_percent`
- detect course completion
- create certificate exactly once
- write completion/progress outbox events

Recommended new internals:

- `ProgressService`
- `StudentProgressRepository`
- `ModuleProgressRepository`
- `CertificateRepository`
- `OutboxRepository`
- optional internal verification/init route for service-to-service use

### C. Course-service needs internal read endpoints for Phase 4

There is no existing Phase 4-ready course internal client contract in the repo today.

Phase 4 likely needs one or both of these internal endpoints added to `course-service`:

1. `GET /courses/internal/{course_id}/enrollment-context`
2. `GET /courses/internal/{course_id}/progress-context`

Recommended payload fields:

- `course_id`
- `title`
- `visibility`
- `current_version_id`
- `max_capacity`
- `prerequisites`
- `modules` with `id`, `title`, `sort_order`, `is_required`

Reasoning:

- enrollment decisions require readiness, capacity, and prerequisites
- progress initialization requires module IDs and required flags
- progress detail/dashboard responses may need titles unless those are denormalized locally

## Important Design Decisions

### 1. Idempotency should use both Redis and the DB

Use the layered approach already implied by docs:

- accept `Idempotency-Key` header and/or request field as contract requires
- optionally cache the successful response in Redis under `idempotency:{key}`
- rely on DB uniqueness `(student_id, course_id)` as the final duplicate prevention rule

Why both:

- Redis improves replay behavior
- DB uniqueness guarantees correctness

### 2. Capacity enforcement should lock per course, not globally

Use `lock:enrollment:{course_id}` with short TTL and keep the critical section narrow:

- fetch course context first if possible
- enter lock
- re-check active enrollment count
- insert enrollment
- release lock

If `max_capacity` is `NULL`, skip locking entirely.

### 3. Prerequisites should be checked locally in enrollment-service

Course prerequisites come from `course-service`; completion evidence should come from the local `enrollment.enrollments` table using status `COMPLETED`.

This is clean because:

- prerequisites are course metadata from the source-of-truth service
- completion state is enrollment lifecycle state owned locally

### 4. Progress initialization must be idempotent

Because enrollment creation and progress initialization cross service boundaries, retries are unavoidable.

Recommended safeguards:

- `progress.student_progress.enrollment_id` is unique
- `progress.module_progress(student_progress_id, module_id)` is unique
- init API in `progress-service` becomes safe to replay without duplicate rows

### 5. Completion and certificate issuance should be owned by progress-service

`progress-service` should be the only service that:

- marks `student_progress.status=COMPLETED`
- creates `certificates`
- emits `CourseCompleted`

It may also notify `enrollment-service` synchronously or via event so enrollment state can transition to `COMPLETED`, depending on final implementation choice.

Recommendation:

- prefer event-driven or internal callback for enrollment completion synchronization
- keep certificate generation local to `progress-service`

### 6. Denormalization gap must be resolved deliberately

There is a mismatch between the documented progress schema and the documented progress API.

Observed mismatch:

- `student_progress` and `module_progress` schemas do not include course/module titles
- progress API responses require `course_title` and `module_title`

Two viable approaches:

1. Denormalize snapshot metadata into progress tables during initialization
2. Fetch titles from `course-service` when building responses

Recommendation:

- prefer denormalizing at initialization for `course_title`, `module_title`, `sort_order`, and `is_required`

Why:

- avoids extra network calls on every dashboard/detail request
- keeps progress reads stable even if course metadata changes later
- fits the certificate snapshot pattern already present in docs

This is the main place where implementation may need to extend the documented Phase 4 schema slightly to satisfy the documented API cleanly.

## Missing Pieces the Plan Must Account For

These do not appear to exist yet in the repo and should be treated as required work, not assumptions:

- Redis dependency wiring in `enrollment-service`
- Redis dependency wiring in `progress-service` if caching or locks are needed there
- enrollment and progress SQLAlchemy models
- enrollment and progress Alembic migrations
- enrollment and progress repositories/services/routes
- internal service clients for course/progress coordination
- internal course endpoints for enrollment/progress context
- internal progress initialization endpoint
- outbox tables/repos in both services
- richer service test fixtures with dependency overrides and DB setup

## Testing Recommendations

### Service test style

Use the more complete `services/course/tests/conftest.py` style as the reference, not the current minimal enrollment/progress fixtures.

That means Phase 4 tests should add:

- async SQLite or test DB fixture
- dependency overrides for DB session and current user
- mock/stub Redis client or real Redis test container
- role-specific clients or auth overrides

### Minimum test matrix

#### Enrollment-service

- unit: prerequisite evaluation
- unit: capacity decision logic
- unit: idempotent replay logic
- integration: enroll happy path
- integration: duplicate enrollment returns existing row
- integration: prerequisites not met
- integration: course not ready
- integration: course full
- integration: cancel enrollment
- concurrency: only `max_capacity` successful requests under parallel load

#### Progress-service

- unit: progress percentage calculation
- unit: completion detection
- unit: certificate number generation uniqueness/format
- integration: initialize progress creates one parent row plus module rows
- integration: repeated initialization is idempotent
- integration: complete module updates overall progress
- integration: final module completion issues exactly one certificate
- integration: dashboard aggregation
- integration: public certificate lookup

### Cross-service contract tests

Because Phase 4 depends on internal HTTP coordination, add focused tests for:

- course context client parsing
- progress init client parsing
- remote error translation to `EduCorpError`

## Risks

### Risk 1: Eventual consistency versus immediate UX

If progress initialization is event-only, the immediate `GET /progress/...` path may be flaky.

Mitigation:

- synchronous init first, event replay second

### Risk 2: Cross-service coupling grows too quickly

If enrollment/progress read too much live course metadata, the services become chatty and fragile.

Mitigation:

- expose a narrow internal course context payload
- denormalize minimal metadata at initialization time

### Risk 3: Capacity races still leak through

Redis lock alone is not enough if DB-level checks are weak.

Mitigation:

- keep DB uniqueness and re-check counts inside the lock window
- test with `asyncio.gather()` concurrency cases

### Risk 4: Partial failure after enrollment creation

If enrollment is committed but progress init fails, the student may have an enrollment without progress.

Mitigation:

- make init idempotent
- persist outbox event for replay/reconciliation
- optionally add a repair path or admin replay later

## Recommended Direction For The Detailed Plan

The next planning pass should expand Phase 4 into a sequence that starts with service boundaries and contracts before deeper implementation.

Recommended order for the plan:

1. Define/confirm internal contracts with `course-service` and `progress-service`
2. Add missing config and dependency wiring (Redis, internal URLs, internal tokens)
3. Add models and migrations in `enrollment-service`
4. Add models and migrations in `progress-service`
5. Add internal HTTP clients
6. Implement enrollment orchestration and progress initialization path
7. Implement progress detail, completion, certificates, and dashboard
8. Add outbox support and event payload definitions
9. Build service-level tests
10. Add concurrency and cross-service contract tests

## Evidence Used

Key repo evidence consulted while preparing this report:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `docs/PHASES.md`
- `docs/API_CONTRACTS.md`
- `docs/DATA_MODELS.md`
- `docs/TESTING_STRATEGY.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `prd.md`
- `shared/educorp_common/auth/dependencies.py`
- `shared/educorp_common/database/base.py`
- `shared/educorp_common/errors.py`
- `shared/educorp_common/schemas/responses.py`
- `services/auth/app/services/auth_service.py`
- `services/auth/app/models/audit_log.py`
- `services/auth/app/models/outbox.py`
- `services/auth/app/repositories/audit_log_repository.py`
- `services/auth/app/repositories/outbox_repository.py`
- `services/course/app/models/course.py`
- `services/course/app/models/module.py`
- `services/course/app/services/course_service.py`
- `services/course/app/services/publishing_client.py`
- `services/publishing/app/config.py`
- `services/publishing/app/models/course_version.py`
- `services/publishing/app/services/course_activation_client.py`
- `services/course/tests/conftest.py`
