# AI Instructor Tools Issues

## Scope

This file covers the instructor-facing Phase 5 enhancement flows.

Primary paths audited:

- `services/ai/app/api/v1/instructor.py`
- `services/ai/app/services/instructor_service.py`
- instructor schemas and job repository behavior

## What Is Already Present

- enhancement queue endpoint exists
- enhancement stream endpoint exists
- job get/list/cancel endpoints exist
- Mongo-backed job persistence exists
- summary/objectives/quiz/glossary prompt templates exist

The gaps are around authorization correctness, retrieval quality, lifecycle durability, and result contract quality.

## Confirmed Gaps

### 1. Instructor RBAC dependency is broken

Evidence:

- `services/ai/app/api/v1/instructor.py:32`
- `shared/educorp_common/auth/dependencies.py:72-83`

Problem:

- `require_roles()` expects varargs
- current code passes a list: `require_roles(["instructor", "admin"])`
- this causes role membership checks to compare a list object against user role strings

Required fix:

- change to `require_roles("instructor", "admin")`
- add tests proving instructor and admin access both succeed while student access fails

### 2. Instructor retrieval strategy is semantically weak

Evidence:

- `services/ai/app/services/instructor_service.py:188-193`
- `services/ai/app/services/instructor_service.py:286-291`
- `_stream_query_hint()` at `services/ai/app/services/instructor_service.py:422-426`

Problem:

- enhancement retrieval uses generic query hints like `summary` or `quiz 10 questions`
- this is a poor substitute for scope-aware course/module content retrieval

Required fix:

- retrieve by explicit scope and content ownership, not by semantic similarity to prompt hints alone
- for module scope, retrieval must focus on that module’s content deterministically

### 3. Module scope is not validated strongly enough

Problem:

- `scope="module"` does not strictly require a real `module_id`
- bad requests can flow through with invalid or empty module targeting

Required fix:

- enforce `module_id` presence and validity whenever module scope is requested

### 4. Job results are not structured by job type

Evidence:

- `services/ai/app/services/instructor_service.py:228-234`
- `services/ai/app/services/instructor_service.py:318-327`

Problem:

- all jobs persist generic `{content, citations}` payloads
- the system does not return structured outputs tailored to summary/objectives/quiz/glossary use cases

Required fix:

- define per-job-type result schemas
- parse and persist typed outputs, not only raw text blobs

### 5. Streaming jobs can remain stuck in `RUNNING` on errors

Evidence:

- `services/ai/app/services/instructor_service.py:171-254`

Problem:

- stream path creates a running job but does not guarantee status transition to `FAILED` on stream-time exceptions

Required fix:

- wrap stream execution with job-state failure handling
- guarantee terminal states for all job outcomes

### 6. Cancellation is shallow and not operationally meaningful

Evidence:

- `services/ai/app/services/instructor_service.py:256-260`

Problem:

- cancellation only flips stored status
- in-flight retrieval and generation continue until later checks

Required fix:

- add cooperative cancellation checks before and during long-running work
- if true interruption is not possible for provider calls, document that and at least prevent post-cancel persistence

### 7. Job execution is not durable across restarts

Evidence:

- `services/ai/app/services/instructor_service.py:130-141` uses `asyncio.create_task()`

Problem:

- queued/running jobs are tied to the API process memory
- process restarts or multiple worker replicas break durability and predictability

Required fix:

- move jobs to a real worker model
- acceptable options:
  - Redis/Celery-backed jobs
  - a proper task worker service
  - another durable async execution mechanism already used in the repo

### 8. Job status response omits important lifecycle details

Problem:

- typed job responses do not surface error payloads and some lifecycle metadata cleanly

Required fix:

- include status, created/started/completed timestamps, error payload, input scope metadata, and typed result summary

## Test Gaps

There is effectively no serious instructor-flow test coverage for:

- RBAC
- module-scope validation
- job lifecycle transitions
- cancel semantics
- failed job persistence
- structured outputs
- stream endpoint behavior

## Implementation Plan

1. Fix RBAC wiring immediately.
2. Replace generic semantic retrieval hints with scope-driven retrieval.
3. Enforce module-scope request validity.
4. Define structured result schemas per job type.
5. Guarantee terminal job states for success, failure, and cancellation.
6. Move job execution off in-process background tasks.
7. Add real tests for instructor route authorization and lifecycle semantics.

## Exit Criteria

- instructor/admin authorization works correctly
- module-scope jobs require a valid module id
- job outputs are structured and useful by type
- jobs survive process restarts or are explicitly backed by a durable queue
- cancel and failure states are trustworthy
- instructor tool tests cover the real lifecycle
