# Testing And Validation Gaps

## Intent

This file defines the test and validation work needed to convert the current Phase 4/5 implementation from “appears implemented” into “provably implemented.”

The current repo has tests, but too many of them are stale, mocked at the wrong level, or detached from the real runtime contracts.

## Core Problem

The current test suite provides false confidence in multiple places.

Examples:

- enrollment unit tests target an old constructor and old methods
- progress unit tests target an old constructor and old completion API
- AI route tests monkeypatch top-level service calls rather than exercising real decision logic
- infra/test execution commands are not reliably provisioned in the runtime environment

## Confirmed Gaps By Area

### Enrollment

Evidence:

- `services/enrollment/tests/unit/test_enrollment_service.py`
- `services/enrollment/tests/integration/test_enrollment_concurrency.py`

Gaps:

- stale service interface assumptions
- concurrency tests not grounded in real Postgres + Redis behavior
- missing assertions for outbox, audit rows, and progress initialization persistence

### Progress

Evidence:

- `services/progress/tests/unit/test_progress_service.py`
- integration tests rely on outdated assumptions per audit

Gaps:

- stale constructor and method usage
- no strong proof that completion, certificate issuance, and enrollment completion are coordinated correctly

### AI Student Assistant

Evidence:

- `services/ai/tests/integration/test_ask_routes.py`

Gaps:

- tests mainly validate route wiring with monkeypatched service results
- no real proof of clarification, refusal, citation validation, entitlement, or rate limiting

### AI Instructor Tools

Gaps:

- almost no meaningful backend coverage for instructor job lifecycle
- no RBAC tests for the broken `require_roles()` usage
- no tests for cancellation, stream failure, structured outputs, or module-scope validation

### Frontend

Gaps:

- no Phase 4 route/page coverage
- no student AI streaming UX coverage
- no instructor job lifecycle UI coverage

## Required Test Pyramid

## Unit Tests

Use for:

- pure status transitions
- certificate number generation rules
- citation parsing/validation helpers
- request validation and adapter logic

Do not use unit tests to pretend cross-service orchestration is covered.

## Integration Tests

Use for:

- enrollment create/cancel/status with real DB persistence
- progress init/detail/complete/certificate with real DB persistence
- AI ask/refusal/clarify against deterministic fake retriever + fake model
- instructor job lifecycle against real persistence and controlled execution backend

## Stack Smoke Tests

Required minimum journeys:

1. Phase 4 smoke:
   - publish-ready course exists
   - student enrolls
   - progress initializes
   - modules complete
   - certificate is issued

2. Phase 5 smoke:
   - enrolled student asks a question
   - cited answer returns
   - irrelevant question returns refusal
   - instructor job can be queued and completed

## Realism Requirements

- at least one enrollment concurrency test must run with real Postgres and Redis semantics
- at least one AI stack-backed test must confirm retrieval + citation payload shape with deterministic fixtures
- startup smoke must fail if migrations or required dependencies are broken

## Deliverables

- rewritten stale unit tests for enrollment and progress
- new integration tests that match current service interfaces
- instructor AI lifecycle tests
- frontend Phase 4/5 route/component tests
- one Phase 4 stack smoke script
- one Phase 5 stack smoke script

## Exit Criteria

- no stale tests remain that target removed constructors or removed methods
- test commands advertised by the repo actually run successfully
- Phase 4 and 5 have at least one realistic end-to-end validation path each
- the team can trust green tests as evidence of actual behavior
