# Enrollment Issues

## Scope

This file covers the enrollment-service gaps for Phase 4.

Primary paths audited:

- `services/enrollment/app/services/enrollment_service.py`
- `services/enrollment/app/api/v1/__init__.py`
- `services/enrollment/app/api/v1/enrollments.py`
- enrollment repositories and tests

## What Is Already Present

- enrollment create endpoint exists
- prerequisite checking exists
- Redis lock based capacity guard exists
- duplicate enrollment handling exists
- enrollment listing/detail/status endpoints exist
- cancellation exists
- outbox writes and audit rows exist

The service is not empty. The problem is that some important details are wrong or only partially implemented.

## Confirmed Gaps

### 1. Internal completion endpoint writes without committing

Evidence:

- `services/enrollment/app/api/v1/__init__.py:42-60`

Problem:

- `mark_enrollment_completed()` calls the service method and returns a response, but never commits the session
- if session lifecycle does not auto-commit here, the internal completion path can silently roll back

Required fix:

- commit on success and rollback on failure in the internal write endpoint path or use the project’s canonical transaction boundary pattern

### 2. Idempotency semantics are stricter and riskier than the phase contract requires

Evidence:

- `services/enrollment/app/services/enrollment_service.py:49-56`
- schema/model definitions around `idempotency_key`

Problem:

- Phase 4 requires same student + same course to return the same enrollment
- current implementation additionally relies on a standalone idempotency key path
- if the key is globally unique rather than user-scoped, accidental collisions become possible

Required fix:

- decide the authoritative contract:
  - either student+course is enough and idempotency key is optional request dedupe metadata
  - or make idempotency uniqueness explicitly scoped by student or actor
- align DB constraints, service logic, and API docs

### 3. Progress initialization currently depends on an architectural shortcut

Evidence:

- `services/enrollment/app/services/enrollment_service.py:240-247`
- `services/enrollment/app/repositories/progress_repository.py`

Problem:

- enrollment directly initializes progress-owned records instead of using the progress service as owner

Required fix:

- move to authoritative internal progress initialization or documented event-driven ownership

### 4. Completion lifecycle is split across two services in conflicting ways

Evidence:

- enrollment owns `mark_completed()` in `services/enrollment/app/services/enrollment_service.py:207-229`
- progress currently bypasses it through direct SQL writes

Problem:

- enrollment owns audit semantics for completion, but progress can mark the row complete without invoking them

Required fix:

- make one path authoritative and remove the bypass

### 5. Cancel side effects are not coordinated with downstream progress/dashboard behavior

Evidence:

- cancellation in `services/enrollment/app/services/enrollment_service.py:186-205`
- progress dashboard uses progress rows rather than enrollment lifecycle truth

Problem:

- cancelled enrollments can remain visible as active learning items depending on downstream query behavior

Required fix:

- define cancellation semantics across services:
  - should progress remain visible but marked cancelled?
  - should dashboard exclude cancelled entries?
  - should completion be blocked after cancellation? it already is at module completion, but dashboard aggregation also needs alignment

## Test Gaps

### Stale unit tests no longer match the real service interface

Evidence:

- `services/enrollment/tests/unit/test_enrollment_service.py:35-57`
- `services/enrollment/tests/unit/test_enrollment_service.py:73-95`

Problem:

- tests instantiate `EnrollmentService` with `course_client` and `progress_client`, but the current constructor is `EnrollmentService(session, redis)`
- tests call `create_enrollment()`, but the current method is `enroll()`

Consequence:

- the tests do not validate the real implementation

### Concurrency tests are too weak

Evidence:

- current concurrency coverage under `services/enrollment/tests/integration/test_enrollment_concurrency.py`

Problem:

- tests do not faithfully prove correctness under real Postgres + Redis locking conditions
- assertions do not sufficiently distinguish expected failure modes from incidental failures

Required fix:

- rewrite concurrency coverage against the current service contract
- add one real-stack test using Postgres and Redis

## Implementation Plan

1. Fix commit behavior on the internal completion endpoint.
2. Decide and document authoritative idempotency semantics.
3. Refactor progress initialization to use the proper ownership boundary.
4. Ensure completion always passes through the enrollment-owned lifecycle path.
5. Align cancellation behavior with progress/dashboard semantics.
6. Rewrite stale unit and integration tests to match the current API and service signatures.

## Exit Criteria

- internal completion persists reliably
- idempotency behavior is explicit and correctly constrained
- enrollment no longer relies on hidden cross-schema writes for progress ownership
- cancellation and completion semantics are consistent across services
- tests validate the real implementation rather than old APIs
