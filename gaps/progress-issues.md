# Progress Issues

## Scope

This file covers the progress-service gaps for Phase 4.

Primary paths audited:

- `services/progress/app/services/progress_service.py`
- `services/progress/app/api/v1/__init__.py`
- progress repositories and tests

## What Is Already Present

- progress detail endpoint exists
- module completion endpoint exists
- dashboard exists
- certificates list/detail exist
- certificate issuance and outbox write exist

This is a meaningful implementation, but several correctness and ownership issues remain.

## Confirmed Gaps

### 1. Internal initialization endpoint writes without committing

Evidence:

- `services/progress/app/api/v1/__init__.py:40-52`

Problem:

- the internal `initialize_progress` endpoint creates records and returns success but does not commit the transaction

Required fix:

- commit on success or adopt a shared transaction wrapper for internal write endpoints

### 2. Progress status defaults are inconsistent with service logic

Evidence:

- service initializes to `NOT_STARTED` in `services/progress/app/services/progress_service.py:181-187`
- model/migration default to `IN_PROGRESS` according to the audit evidence

Problem:

- initial progress state can differ depending on code path or persistence default
- this creates contract ambiguity for dashboard logic, progress detail, and test expectations

Required fix:

- choose one initial status and align model, migration, service, and API examples
- based on Phase 4 wording, `NOT_STARTED` is the better initial state

### 3. Completion path bypasses enrollment-service ownership and audit semantics

Evidence:

- `services/progress/app/services/progress_service.py:142-155`
- `services/progress/app/repositories/enrollment_repository.py:46-62`

Problem:

- progress directly updates `enrollment.enrollments`
- this bypasses enrollment-owned lifecycle logic and audit generation

Required fix:

- invoke the enrollment-owned internal completion contract instead of writing directly into another service’s schema

### 4. Dashboard semantics ignore enrollment lifecycle truth

Evidence:

- `services/progress/app/services/progress_service.py:216-246`

Problem:

- dashboard aggregates `progress.student_progress` joined with course title
- it does not account for enrollment cancellation or lifecycle status beyond what happens to exist in progress rows

Required fix:

- define the dashboard source of truth
- if dashboard represents active learning state, it must account for enrollment lifecycle

### 5. Optional-module handling is incomplete or unsafe

Evidence:

- `ProgressInitRequest` includes `is_required` per module
- `services/progress/app/services/progress_service.py:190-198` creates module progress rows without using `is_required`
- completion percentage is based on all module progress rows in `services/progress/app/services/progress_service.py:133-145`

Problem:

- if optional modules are ever passed to this API, completion percentages and course completion can become wrong

Required fix:

- either:
  - store requiredness in module progress and count only required modules, or
  - guarantee the init contract only includes required modules and enforce that at the boundary

### 6. Certificate generation depends on cross-schema reads for course and user identity

Evidence:

- `services/progress/app/services/progress_service.py:290-295`

Problem:

- progress reads course title and user full name from other service-owned schemas

Required fix:

- replace with explicit service contracts or a materialized projection strategy

## Test Gaps

### Unit tests are stale and no longer instantiate the real service correctly

Evidence:

- `services/progress/tests/unit/test_progress_service.py:17-18`
- `services/progress/tests/unit/test_progress_service.py:38-52`

Problem:

- tests pass `enrollment_client` into a constructor that no longer accepts it
- tests call `complete_module()` using an outdated signature

### Integration tests monkeypatch non-authoritative paths

Problem:

- current integration coverage does not prove the real persistence and lifecycle behavior under the current implementation shape

Required fix:

- rewrite tests around the real service contracts and one realistic stack-backed path

## Implementation Plan

1. Fix commit behavior for internal progress initialization.
2. Align initial progress status defaults to one contract.
3. Remove direct progress-side enrollment completion writes.
4. Decide dashboard behavior for cancelled enrollments and implement it explicitly.
5. Fix required-vs-optional module semantics.
6. Rewrite tests to match the current service interface and lifecycle.

## Exit Criteria

- internal init persists correctly
- initial status is deterministic and documented
- course completion flows through the proper owning service
- dashboard output matches enrollment lifecycle semantics
- completion percentages are correct for required modules
- tests validate the real implementation
