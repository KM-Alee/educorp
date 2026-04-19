# Cross-Service Contracts

## Intent

This file addresses the biggest architectural contradiction in the current Phase 4/5 implementation: several services directly query or mutate other services' schemas, even though project guidance explicitly says not to query across service schema boundaries.

This is not just a style issue. It is the main reason the system currently looks functional while remaining fragile, under-tested, and difficult to evolve safely.

## Documented Architecture Rule

Project guidance states:

- `AGENTS.md`: never query across service schema boundaries; use events or HTTP

## Current Violations

### Enrollment service directly reads course and publishing schemas

Evidence:

- `services/enrollment/app/repositories/course_repository.py:25-74`

Current behavior:

- reads `course.courses`
- joins `publishing.course_versions`
- reads `course.modules`

Impact:

- enrollment is coupled to course and publishing table structure
- any future schema isolation, DB permission tightening, or service extraction will break enrollment

### Enrollment service directly writes progress schema

Evidence:

- `services/enrollment/app/repositories/progress_repository.py`

Current behavior:

- enrollment initializes progress rows by writing directly into progress-owned tables

Impact:

- the intended service boundary between enrollment and progress is bypassed
- the existing internal progress HTTP API becomes mostly decorative

### Progress service directly reads and mutates enrollment, course, and auth data

Evidence:

- `services/progress/app/repositories/enrollment_repository.py:25-62`
- `services/progress/app/repositories/course_repository.py`
- `services/progress/app/repositories/user_repository.py`
- `services/progress/app/repositories/module_progress_repository.py`

Current behavior:

- reads enrollment state directly
- marks enrollment complete directly in the enrollment schema
- reads course title directly
- reads user names directly from auth-owned data

Impact:

- progress completion bypasses enrollment-service business rules and audit handling
- cross-service invariants are enforced implicitly and incompletely

### AI service directly reads course, publishing, and enrollment schemas

Evidence:

- `services/ai/app/repositories/entitlement_repository.py:15-63`

Impact:

- AI entitlement and readiness depend on shared-schema assumptions
- this is another hidden monolith pattern inside a nominal microservice topology

## Additional Contract Drift

### Internal HTTP clients exist but are not the primary runtime path

Evidence:

- `services/enrollment/app/services/course_client.py`
- `services/enrollment/app/services/progress_client.py`
- `services/progress/app/services/enrollment_client.py`

Problem:

- these client abstractions suggest HTTP-based service interaction, but the actual implementations bypass them through direct SQL
- tests and architecture become harder to reason about because the visible abstraction is not the real one

### Completion path bypasses enrollment business logic

Evidence:

- progress writes completion via `services/progress/app/repositories/enrollment_repository.py:46-62`
- enrollment has its own completion workflow and audit creation in `services/enrollment/app/services/enrollment_service.py:207-229`

Problem:

- completion status may be updated without passing through the service that owns the lifecycle and audit semantics

## Decision Required

An implementation agent must choose and document one of these two paths.

### Path A: honor service boundaries

Recommended.

Approach:

- move enrollment-to-progress initialization onto the internal progress API or event-driven flow
- move progress-to-enrollment completion onto the internal enrollment API or event-driven flow
- move AI entitlement and ready-version checks behind internal APIs owned by course/publishing/enrollment
- reduce direct SQL access to service-owned schemas

Benefits:

- aligns with project architecture
- enables future schema isolation and permission hardening
- makes tests map to the real deployment model

Costs:

- requires more endpoint and contract work now
- may require shared internal auth conventions and more explicit service APIs

### Path B: explicitly bless shared-database integration for selected read paths

Not recommended unless the architecture docs are intentionally being changed.

Approach:

- formally document which services are allowed shared-schema access
- update architecture docs and security assumptions accordingly
- keep direct SQL but harden it with realistic tests and ownership rules

Risks:

- contradicts existing project guidance
- creates a pseudo-microservice system that is harder to secure and evolve

## Recommended Remediation

Choose Path A.

Implement the following:

1. Make cross-service runtime flows explicit.
2. Use internal HTTP endpoints or event-driven synchronization for owned state changes.
3. Keep direct SQL only for temporary transitional read paths if absolutely necessary, and clearly mark them as transitional.
4. Remove dead abstractions where the client exists but the repository shortcut is what really runs.

## Concrete Work Items

### Enrollment to progress initialization

- make `POST /progress/internal/init` the authoritative initialization path
- ensure it commits and is idempotent
- remove or deprecate direct progress-table writes from enrollment

### Progress to enrollment completion

- make `POST /enrollment/internal/enrollments/{id}/complete` the authoritative completion path
- ensure it commits and records audit data
- stop direct progress-side updates of enrollment tables

### AI entitlement and ready-version checks

- define internal read APIs or a materialized/access-optimized projection strategy
- avoid direct cross-schema joins inside AI service

## Exit Criteria

- no Phase 4/5 business-critical flow depends on hidden cross-schema writes
- service-to-service contracts are explicit and testable
- dead or misleading client abstractions are removed or made authoritative
- architecture docs and code agree on the integration model
