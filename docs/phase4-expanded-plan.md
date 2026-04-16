# Phase 4 Expanded Plan

Date: 2026-04-16

## Objective

Implement Phase 4 for EduCorp:

- student enrollment with idempotency, prerequisite checks, and capacity enforcement
- progress initialization after enrollment
- module completion and overall course progress tracking
- course completion and certificate issuance
- enrollment and progress lifecycle event emission via transactional outbox
- test coverage for happy-path, failure-path, idempotency, and concurrency behavior

This plan is implementation-ready and grounded in the current repository state documented in `docs/phase4-research-report.md`.

## Current State Summary

### What already exists

- `services/enrollment` and `services/progress` both have working FastAPI app factories, DB session bootstrapping, and health endpoints.
- `shared/educorp_common` already provides:
  - auth dependencies and role guards
  - SQLAlchemy base/mixins
  - standard response envelopes
  - common error types
- `services/auth` already demonstrates:
  - repository + service orchestration
  - audit log model/repository pattern
  - transactional outbox model/repository pattern
  - Redis dependency wiring
- `services/course` and `services/publishing` already demonstrate:
  - internal HTTP client wrappers with `httpx.AsyncClient`
  - internal auth via `X-Internal-Service-Token`
  - correlation ID propagation
- `services/course` already has the upstream fields Phase 4 needs:
  - `title`
  - `max_capacity`
  - `prerequisites`
  - `visibility`
  - `current_version_id`
  - module `title`, `sort_order`, `is_required`

### What does not exist yet

- no enrollment domain models, schemas, repositories, services, or routes
- no progress domain models, schemas, repositories, services, or routes
- no enrollment/progress migrations for Phase 4 tables
- no Redis wiring in `enrollment-service`
- no internal course context endpoints dedicated to Phase 4 needs
- no internal progress initialization endpoint
- no outbox implementation in enrollment or progress services
- no realistic test fixtures in enrollment/progress beyond minimal `AsyncClient`

## Assumptions

1. Phase 4 work is allowed because the user explicitly asked for Phase 4 planning and research.
2. Service boundaries remain intact: no cross-schema SQL queries between services.
3. Enrollment decisions are owned by `enrollment-service`.
4. Progress state and certificate issuance are owned by `progress-service`.
5. Immediate progress availability after enrollment is required by the documented Phase 4 outcome, so pure eventual consistency is not sufficient.
6. Internal service-to-service HTTP with internal auth tokens is acceptable because the repo already uses that pattern.

## Non-Goals

1. Implementing Phase 5 AI entitlement and query behavior.
2. Building analytics/notification consumers beyond writing the outbox events Phase 4 requires.
3. Frontend implementation for Phase 4 UI flows.
4. Full ops tooling or replay systems beyond the minimum outbox shape needed now.

## Detailed Context Map

### Enrollment service: likely files to create or modify

#### Existing files to modify

- `services/enrollment/app/config.py`
- `services/enrollment/app/dependencies.py`
- `services/enrollment/app/api/v1/__init__.py`
- `services/enrollment/app/main.py` if extra startup dependencies are needed
- `services/enrollment/alembic/env.py` only if metadata import wiring needs updates
- `services/enrollment/tests/conftest.py`

#### New or expanded modules expected

- `services/enrollment/app/models/__init__.py`
- `services/enrollment/app/models/enrollment.py`
- `services/enrollment/app/models/enrollment_audit.py`
- `services/enrollment/app/models/outbox.py`
- `services/enrollment/app/repositories/enrollment_repository.py`
- `services/enrollment/app/repositories/enrollment_audit_repository.py`
- `services/enrollment/app/repositories/outbox_repository.py`
- `services/enrollment/app/repositories/__init__.py`
- `services/enrollment/app/schemas/enrollment.py`
- `services/enrollment/app/schemas/internal.py`
- `services/enrollment/app/schemas/__init__.py`
- `services/enrollment/app/services/enrollment_service.py`
- `services/enrollment/app/services/course_client.py`
- `services/enrollment/app/services/progress_client.py`
- `services/enrollment/app/services/__init__.py`
- `services/enrollment/alembic/versions/<phase4_migration>.py`
- `services/enrollment/tests/unit/test_enrollment_service.py`
- `services/enrollment/tests/integration/test_enrollment_api.py`
- `services/enrollment/tests/integration/test_enrollment_concurrency.py`

### Progress service: likely files to create or modify

#### Existing files to modify

- `services/progress/app/config.py`
- `services/progress/app/dependencies.py`
- `services/progress/app/api/v1/__init__.py`
- `services/progress/app/main.py` if extra startup dependencies are needed
- `services/progress/alembic/env.py` only if metadata import wiring needs updates
- `services/progress/tests/conftest.py`

#### New or expanded modules expected

- `services/progress/app/models/__init__.py`
- `services/progress/app/models/student_progress.py`
- `services/progress/app/models/module_progress.py`
- `services/progress/app/models/certificate.py`
- `services/progress/app/models/outbox.py`
- `services/progress/app/repositories/student_progress_repository.py`
- `services/progress/app/repositories/module_progress_repository.py`
- `services/progress/app/repositories/certificate_repository.py`
- `services/progress/app/repositories/outbox_repository.py`
- `services/progress/app/repositories/__init__.py`
- `services/progress/app/schemas/progress.py`
- `services/progress/app/schemas/internal.py`
- `services/progress/app/schemas/__init__.py`
- `services/progress/app/services/progress_service.py`
- `services/progress/app/services/__init__.py`
- `services/progress/alembic/versions/<phase4_migration>.py`
- `services/progress/tests/unit/test_progress_service.py`
- `services/progress/tests/integration/test_progress_api.py`
- `services/progress/tests/integration/test_progress_init_internal.py`

### Course service: upstream contract work likely needed

#### Existing files to modify

- `services/course/app/api/v1/<course_router_module>.py`
- `services/course/app/services/course_service.py`
- `services/course/app/schemas/course.py` or a new internal schema module
- `services/course/app/dependencies.py` if internal auth dependency is needed
- tests covering the new internal endpoint(s)

#### Likely new surface area

- internal route(s) for enrollment/progress context
- internal schema for course/module snapshot payload

### Shared and reference files to follow

- `shared/educorp_common/auth/dependencies.py`
- `shared/educorp_common/database/base.py`
- `shared/educorp_common/errors.py`
- `shared/educorp_common/schemas/responses.py`
- `services/auth/app/models/audit_log.py`
- `services/auth/app/repositories/audit_log_repository.py`
- `services/auth/app/models/outbox.py`
- `services/auth/app/repositories/outbox_repository.py`
- `services/course/app/services/publishing_client.py`
- `services/publishing/app/services/course_activation_client.py`
- `services/course/tests/conftest.py`

### External dependencies and upstream contracts

- `docs/PHASES.md`
- `docs/API_CONTRACTS.md`
- `docs/DATA_MODELS.md`
- `docs/TESTING_STRATEGY.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `prd.md`

## Key Design Decisions

### Decision 1: authoritative ownership split

- `enrollment-service` owns:
  - enrollment creation
  - duplicate prevention
  - prerequisite checks
  - capacity enforcement
  - enrollment cancellation
  - enrollment lifecycle audit
- `progress-service` owns:
  - progress initialization
  - module completion
  - completion detection
  - certificate generation
  - progress lifecycle events

### Decision 2: internal HTTP, not cross-schema reads

To respect schema isolation, Phase 4 will use internal HTTP endpoints instead of querying `course.*` or `publishing.*` tables from enrollment/progress services.

### Decision 3: sync initialization plus outbox replay safety

To satisfy immediate progress visibility:

- `enrollment-service` will create the enrollment and then call an internal progress-init endpoint synchronously.
- `enrollment-service` will still write `EnrollmentCreated` to its outbox.
- `progress-service` init must be idempotent so retries and reconciliation are safe.

### Decision 4: metadata denormalization in progress

The API contracts require `course_title` and `module_title`, but the documented progress schema does not include those fields. The plan therefore assumes the progress schema will be extended minimally to store a stable snapshot of:

- `course_title`
- `module_title`
- `sort_order`
- `is_required`

This avoids repeated cross-service enrichment for every progress read.

### Decision 5: layered correctness for idempotency and capacity

- DB uniqueness protects against duplicate enrollment rows.
- Redis idempotency cache improves replay behavior.
- Redis lock protects course capacity under concurrency.

## Expanded Execution Plan

## Phase 1: Contract Definition and Wiring

### Step 1.1: confirm internal service boundaries

Files:

- `docs/phase4-research-report.md`
- `docs/phase4-expanded-plan.md`
- service config files for enrollment, progress, and course

Actions:

- treat `enrollment-service` as the only place that decides whether a student can enroll
- treat `progress-service` as the only place that can create/update progress and certificates
- treat `course-service` as the source of course/module metadata and readiness context

Verify:

- all downstream steps respect schema isolation

### Step 1.2: define the internal course context contract

Likely files:

- `services/course/app/schemas/internal.py` or equivalent
- `services/course/app/services/course_service.py`
- `services/course/app/api/v1/...`

Actions:

- define a narrow internal read payload for a course enrollment context
- include at minimum:
  - `course_id`
  - `title`
  - `visibility`
  - `current_version_id`
  - `max_capacity`
  - `prerequisites`
  - ordered `modules` with `id`, `title`, `sort_order`, `is_required`
- decide whether one endpoint can serve both enrollment and progress initialization or whether two endpoints are cleaner

Verify:

- payload contains every field needed without any cross-schema fallback

### Step 1.3: define the internal progress-init contract

Likely files:

- `services/progress/app/schemas/internal.py`
- `services/progress/app/api/v1/...`
- `services/enrollment/app/services/progress_client.py`

Actions:

- define an internal endpoint that receives the full enrollment context needed to initialize progress idempotently
- recommended request fields:
  - `enrollment_id`
  - `student_id`
  - `course_id`
  - `course_title`
  - module snapshot list
  - `started_at` or `enrolled_at`

Verify:

- the contract is sufficient for progress init without a secondary course-service call

### Step 1.4: add config for service-to-service coordination

Likely files:

- `services/enrollment/app/config.py`
- `services/progress/app/config.py`
- `services/course/app/config.py` if not already sufficient

Actions:

- add `course_service_url` to enrollment settings
- add `progress_service_url` to enrollment settings
- add `internal_service_token` to enrollment/progress settings
- add any Redis TTL or lock timeout settings needed for Phase 4

Verify:

- settings objects expose all URLs/tokens used by new clients

### Step 1.5: add Redis dependencies to enrollment-service

Likely files:

- `services/enrollment/app/dependencies.py`
- `services/enrollment/app/main.py`

Actions:

- mirror the auth-service pattern for Redis client lifecycle
- expose `get_redis()` dependency
- initialize Redis in lifespan startup and close it on shutdown

Verify:

- enrollment routes/services can request Redis through dependency injection

## Phase 2: Enrollment Domain Models and Persistence

### Step 2.1: create enrollment ORM models

Likely files:

- `services/enrollment/app/models/enrollment.py`
- `services/enrollment/app/models/enrollment_audit.py`
- `services/enrollment/app/models/outbox.py`
- `services/enrollment/app/models/__init__.py`

Actions:

- implement `Enrollment` using `Base`, `UUIDPrimaryKeyMixin`, and `TimestampMixin`
- implement status constraint for `ENROLLED`, `CANCELLED`, `COMPLETED`
- implement uniqueness for `(student_id, course_id)`
- implement optional unique idempotency key index
- implement `EnrollmentAudit` with action/details/correlation fields
- add outbox model matching auth-service pattern but scoped to schema `enrollment`

Verify:

- metadata imports cleanly
- all indexes/constraints align with docs

### Step 2.2: create enrollment repositories

Likely files:

- `services/enrollment/app/repositories/enrollment_repository.py`
- `services/enrollment/app/repositories/enrollment_audit_repository.py`
- `services/enrollment/app/repositories/outbox_repository.py`

Actions:

- add read/write methods for:
  - get by id
  - get by student/course
  - list by student with filters and pagination
  - count active enrollments for a course
  - create/update enrollment
  - lookup by idempotency key if stored in DB
- add audit create method
- mirror auth outbox repository shape

Verify:

- repositories use `flush()` and do not commit directly

### Step 2.3: add enrollment Alembic migration

Likely files:

- `services/enrollment/alembic/versions/<phase4_migration>.py`

Actions:

- create `enrollments`, `enrollment_audit`, and `outbox` tables and indexes
- ensure schema is `enrollment`

Verify:

- migration matches ORM definitions

## Phase 3: Progress Domain Models and Persistence

### Step 3.1: create progress ORM models

Likely files:

- `services/progress/app/models/student_progress.py`
- `services/progress/app/models/module_progress.py`
- `services/progress/app/models/certificate.py`
- `services/progress/app/models/outbox.py`
- `services/progress/app/models/__init__.py`

Actions:

- implement `StudentProgress`
- implement `ModuleProgress`
- implement `Certificate`
- add progress outbox model using the auth pattern under schema `progress`
- include denormalized snapshot fields required by the API surface

Recommended extra fields beyond base docs:

- `student_progress.course_title`
- `module_progress.module_title`
- `module_progress.sort_order`
- `module_progress.is_required`

Verify:

- API response requirements can be fulfilled locally from progress DB reads

### Step 3.2: create progress repositories

Likely files:

- `services/progress/app/repositories/student_progress_repository.py`
- `services/progress/app/repositories/module_progress_repository.py`
- `services/progress/app/repositories/certificate_repository.py`
- `services/progress/app/repositories/outbox_repository.py`

Actions:

- add CRUD/query methods for initialization, progress detail, dashboard, and certificate lookup
- add lookup by `enrollment_id`
- add list for dashboard and certificate index
- add exactly-once certificate creation helper by enrollment

Verify:

- repository methods support both detail and aggregation endpoints without awkward service-layer SQL

### Step 3.3: add progress Alembic migration

Likely files:

- `services/progress/alembic/versions/<phase4_migration>.py`

Actions:

- create `student_progress`, `module_progress`, `certificates`, and `outbox` tables/indexes
- include uniqueness for:
  - `student_progress.enrollment_id`
  - `(student_progress_id, module_id)`
  - `certificates.enrollment_id`
  - `certificates.certificate_number`

Verify:

- migration matches both docs and the chosen denormalized fields

## Phase 4: Internal Clients and Internal Endpoints

### Step 4.1: implement enrollment-service course client

Likely files:

- `services/enrollment/app/services/course_client.py`

Actions:

- follow `PublishingClient` / `CourseActivationClient` patterns
- send `X-Internal-Service-Token`
- propagate `X-Correlation-Id`
- translate remote errors into `EduCorpError`
- expose a method to fetch the course enrollment/progress context

Verify:

- client handles non-JSON and structured error bodies cleanly

### Step 4.2: implement enrollment-service progress client

Likely files:

- `services/enrollment/app/services/progress_client.py`

Actions:

- implement internal call used after successful enrollment creation
- make it retry-safe from the caller perspective

Verify:

- duplicate init requests do not break the flow

### Step 4.3: implement course internal context route

Likely files:

- `services/course/app/api/v1/...`
- `services/course/app/services/course_service.py`
- `services/course/app/schemas/internal.py`

Actions:

- add internal-only endpoint guarded by internal token
- return the narrow course snapshot required by enrollment/progress

Verify:

- endpoint exposes only the fields Phase 4 needs

### Step 4.4: implement progress internal init route

Likely files:

- `services/progress/app/api/v1/...`
- `services/progress/app/services/progress_service.py`
- `services/progress/app/schemas/internal.py`

Actions:

- add internal-only route to initialize progress idempotently
- create one `student_progress` row plus one `module_progress` row per module
- if already initialized, return existing state rather than erroring

Verify:

- repeated init calls are safe and return the same logical result

## Phase 5: Enrollment Orchestration and Public API

### Step 5.1: create enrollment request/response schemas

Likely files:

- `services/enrollment/app/schemas/enrollment.py`

Actions:

- add request model for enrollment creation
- add response models for list/detail/status
- add pagination/list query schema if helpful

Verify:

- schema shapes match `docs/API_CONTRACTS.md`

### Step 5.2: implement enrollment business service

Likely files:

- `services/enrollment/app/services/enrollment_service.py`

Actions:

- orchestrate the happy path:
  - parse current student identity
  - enforce student role if needed
  - resolve idempotency replay
  - fetch course context via client
  - ensure course is READY/enrollable
  - check prerequisites using local completed enrollments
  - acquire course lock if `max_capacity` is set
  - re-check active enrollment count
  - create enrollment row
  - write audit row
  - write outbox event
  - commit enrollment transaction
  - call progress init synchronously
- implement read/list/cancel flows

Verify:

- happy path yields a stable enrollment ID
- duplicate enrollment returns existing result
- course-full and prereq failures map to `409`

### Step 5.3: implement idempotency behavior explicitly

Likely files:

- `services/enrollment/app/services/enrollment_service.py`
- possibly a small Redis utility helper

Actions:

- decide whether to accept idempotency from request body, header, or both
- use Redis `idempotency:{key}` cache for replay acceleration
- still rely on DB uniqueness for correctness

Verify:

- replay with same key returns same enrollment payload

### Step 5.4: implement public enrollment routes

Likely files:

- `services/enrollment/app/api/v1/__init__.py` or split router modules

Actions:

- add:
  - `POST /enrollments`
  - `GET /enrollments`
  - `GET /enrollments/{enrollment_id}`
  - `POST /enrollments/{enrollment_id}/cancel`
  - `GET /courses/{course_id}/enrollment-status`
- keep handlers thin and delegate to service layer

Verify:

- route prefixes line up with current app mounting

### Step 5.5: add enrollment cache invalidation where useful

Likely files:

- enrollment service layer

Actions:

- cache enrollment-status results only if simple and low-risk
- invalidate `cache:enrolled:{user_id}:{course_id}` on create/cancel/complete transitions

Verify:

- cached status never contradicts DB state after writes

## Phase 6: Progress Orchestration and Public API

### Step 6.1: create progress request/response schemas

Likely files:

- `services/progress/app/schemas/progress.py`

Actions:

- add models for:
  - detailed progress response
  - module completion response
  - dashboard response
  - certificate list/detail response

Verify:

- all required API fields are representable from local progress data

### Step 6.2: implement progress initialization logic

Likely files:

- `services/progress/app/services/progress_service.py`

Actions:

- create the parent `student_progress` row
- create ordered `module_progress` rows
- mark initial status as `NOT_STARTED` or `IN_PROGRESS` according to final choice
- ensure repeated init calls are safe

Verify:

- exactly one progress tree exists per enrollment

### Step 6.3: implement module completion logic

Likely files:

- `services/progress/app/services/progress_service.py`

Actions:

- verify enrollment ownership or admin override
- mark the target module complete if not already complete
- update timestamps
- recompute overall progress using required modules
- update `last_activity_at`
- write `ProgressUpdated` outbox event if desired

Verify:

- repeated completion of the same module is idempotent or harmless
- overall progress percent is stable and correct

### Step 6.4: implement course completion and certificate issuance

Likely files:

- `services/progress/app/services/progress_service.py`
- `services/progress/app/repositories/certificate_repository.py`

Actions:

- detect when all required modules are complete
- transition `student_progress` to `COMPLETED`
- generate certificate exactly once
- write `CourseCompleted` outbox event
- decide how enrollment completion sync is handled:
  - internal callback to enrollment-service, or
  - event-driven sync later

Verify:

- final completion response includes certificate metadata
- a second completion attempt does not create a duplicate certificate

### Step 6.5: implement dashboard and certificate reads

Likely files:

- `services/progress/app/api/v1/__init__.py` or split router modules
- `services/progress/app/services/progress_service.py`

Actions:

- add:
  - `GET /progress/enrollments/{enrollment_id}`
  - `POST /progress/enrollments/{enrollment_id}/modules/{module_id}/complete`
  - `GET /progress/dashboard`
  - `GET /progress/certificates`
  - `GET /progress/certificates/{certificate_id}`
- ensure certificate detail can be public while hiding unsafe data

Verify:

- responses match `docs/API_CONTRACTS.md`

## Phase 7: Eventing, Auditing, and Coordination Gaps

### Step 7.1: define enrollment outbox events

Likely files:

- enrollment outbox model/repository/service code
- event payload helpers if added

Actions:

- emit at least:
  - `EnrollmentCreated`
  - `EnrollmentCancelled`
- include standard envelope shape from docs

Verify:

- outbox rows are written in the same transaction as enrollment changes

### Step 7.2: define progress outbox events

Likely files:

- progress outbox model/repository/service code

Actions:

- emit at least:
  - `CourseCompleted`
- optionally emit `ProgressUpdated` when worthwhile

Verify:

- completion and certificate issuance write events atomically with progress updates

### Step 7.3: add enrollment audit behavior

Likely files:

- `services/enrollment/app/models/enrollment_audit.py`
- `services/enrollment/app/repositories/enrollment_audit_repository.py`
- `services/enrollment/app/services/enrollment_service.py`

Actions:

- record key actions such as:
  - `ENROLLED`
  - `CANCELLED`
  - `PREREQUISITE_CHECK`
  - `CAPACITY_CHECK`
  - `COMPLETED` if enrollment state is synchronized later

Verify:

- audit rows include actor ID and correlation ID

## Phase 8: Testing Plan

### Step 8.1: replace minimal test fixtures with realistic service fixtures

Likely files:

- `services/enrollment/tests/conftest.py`
- `services/progress/tests/conftest.py`

Actions:

- mirror the more complete course-service fixture style
- provide:
  - test DB engine/session
  - app dependency overrides
  - current user overrides for student/admin
  - mock Redis or fake lock behavior
  - mocked internal clients where useful

Verify:

- tests can isolate business logic without starting full infra

### Step 8.2: add enrollment unit tests

Likely files:

- `services/enrollment/tests/unit/test_enrollment_service.py`

Coverage:

- prerequisite pass/fail
- course-ready validation
- duplicate detection
- course-full decision logic
- cancel flow rules

### Step 8.3: add enrollment integration tests

Likely files:

- `services/enrollment/tests/integration/test_enrollment_api.py`

Coverage:

- enroll happy path
- idempotent replay path
- already enrolled without idempotency key
- prerequisites not met
- course not ready
- course full
- list/detail/status endpoints
- cancel endpoint

### Step 8.4: add concurrency tests

Likely files:

- `services/enrollment/tests/integration/test_enrollment_concurrency.py`

Coverage:

- parallel enrollment requests against `max_capacity=1`
- confirm only one succeeds and the rest reject
- confirm duplicates do not create multiple rows

### Step 8.5: add progress unit tests

Likely files:

- `services/progress/tests/unit/test_progress_service.py`

Coverage:

- progress percentage calculation
- completion detection
- idempotent initialization
- certificate number generation

### Step 8.6: add progress integration tests

Likely files:

- `services/progress/tests/integration/test_progress_api.py`
- `services/progress/tests/integration/test_progress_init_internal.py`

Coverage:

- internal init creates progress tree
- repeated init is safe
- progress detail payload shape
- module completion updates overall progress
- final module creates one certificate
- dashboard aggregation
- public certificate verification

### Step 8.7: add client contract tests

Likely files:

- enrollment service tests around `course_client.py`
- enrollment service tests around `progress_client.py`
- course-service tests for internal context endpoint

Coverage:

- successful JSON parsing
- remote structured error handling
- unexpected body handling
- internal auth header behavior

## Verification Checkpoints

### Checkpoint A: after contracts and config

- internal endpoint shapes are decided
- service config contains all needed URLs/tokens
- Redis dependency is wired in enrollment-service

### Checkpoint B: after models and migrations

- enrollment and progress metadata import cleanly
- migrations can generate/apply without schema errors

### Checkpoint C: after orchestration

- `POST /enrollments` creates one enrollment and one progress tree
- `GET /progress/enrollments/{id}` works immediately after enrollment

### Checkpoint D: after completion flow

- completing all required modules transitions progress to `COMPLETED`
- one certificate is issued
- `CourseCompleted` outbox row exists

### Checkpoint E: after tests

- unit, integration, and concurrency tests pass

## Rollback and Containment Strategy

### If internal service contract work blocks progress

- stop before implementing orchestration against unstable contracts
- land contract/schema work first in course/progress services

### If sync progress initialization proves unstable

- keep enrollment creation and outbox emission as the durable core
- make progress init retryable and repairable
- avoid hiding partial failure; surface a clear internal error path during development

### If denormalization expands beyond the intended scope

- restrict the snapshot fields to only those required by current APIs
- avoid copying large course payloads into progress DB

## Open Questions

1. Should duplicate enrollment return `201` with `meta.idempotent_hit=true`, or preserve the `409` example shown in `docs/API_CONTRACTS.md`?
2. Should progress initialization mark the course as `NOT_STARTED` until the first module action, or `IN_PROGRESS` at enrollment time?
3. Should enrollment completion be synchronized back from `progress-service` to `enrollment-service` via an internal callback now, or only via outbox/event consumption later?
4. What exact certificate number format should be considered canonical beyond the example `SC-2026-00042`?
5. Should enrollment cancellation preserve progress rows as historical records, or mark them terminal and hide them from normal student views?

## Exit Criteria Mapped to Phase 4

### Enrollment

- `POST /enrollments` is idempotent and duplicate-safe
- prerequisites are enforced from course metadata plus local completion state
- course capacity is enforced under concurrency using Redis lock plus DB checks
- enrollment list/detail/status endpoints are implemented
- enrollment cancellation exists

### Progress

- progress is initialized exactly once per enrollment
- progress detail shows module-level status immediately after enrollment
- module completion updates overall progress accurately
- final completion issues exactly one certificate
- dashboard and certificate endpoints work

### Eventing and auditing

- enrollment lifecycle writes outbox rows
- progress completion writes outbox rows
- enrollment audit records key transitions/checks

### Testing

- unit tests cover business rules
- integration tests cover API behavior
- concurrency tests cover capacity correctness
- contract tests cover internal service client behavior

## Recommended Implementation Order Summary

1. Internal contracts and config wiring
2. Enrollment models, repositories, and migration
3. Progress models, repositories, and migration
4. Internal course/progress endpoints and clients
5. Enrollment public API and orchestration
6. Progress public API and completion logic
7. Outbox and audit behavior
8. Unit, integration, concurrency, and contract tests
