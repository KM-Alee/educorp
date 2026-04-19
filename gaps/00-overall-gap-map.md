# Overall Gap Map

## Executive Summary

Phase 4 and 5 were implemented far enough to create the illusion of feature completeness, but the current state is not reliable enough to treat as done. The repo contains core APIs, models, and some tests, yet several important paths are incomplete, contradictory, or untested in realistic conditions.

The dominant failure modes are:

- direct cross-schema coupling between services despite the documented architecture rule
- internal endpoints that perform writes without committing
- stale tests that no longer match current service interfaces
- frontend coverage that stops short of the actual Phase 4 experience
- AI flows that expose endpoints but miss key correctness guarantees around clarification, citations, role checks, and durable jobs
- infrastructure/startup gaps that make end-to-end validation non-deterministic

## Requirement Status By Area

### Phase 4

Implemented in meaningful form:

- enrollment create/list/detail/cancel/status APIs exist
- prerequisite and capacity checks exist
- progress initialization path exists
- module completion exists
- course completion and certificate issuance exist
- dashboard and certificate endpoints exist
- outbox writes exist

Not fully correct or complete:

- service boundary rules are violated by cross-schema reads and writes
- internal write APIs do not commit
- progress state defaults are inconsistent
- cancellation and dashboard state can drift
- tests are stale and low-confidence
- frontend Phase 4 experience is largely missing

### Phase 5

Implemented in meaningful form:

- non-streaming ask route exists
- streaming ask route exists
- LangGraph-like Q&A pipeline exists
- caching and rate limiting exist
- instructor enhancement routes and job records exist
- Mongo-backed AI job storage exists

Not fully correct or complete:

- instructor RBAC is broken
- clarification branch is effectively unreachable
- citation validity is not enforced
- streaming path diverges from the main Q&A state machine
- instructor retrieval strategy is weak and often wrong
- instructor job lifecycle is not durable enough
- admin rate-limit bypass is missing
- frontend Phase 5 UX is partial and not robust
- tests do not cover the real failure surfaces

## Severity Ranking

## P0

- Fix infrastructure and startup blockers that make Phase 4/5 validation unreliable.
- Resolve cross-service contract violations and choose the real integration pattern.
- Fix internal write endpoints that omit commit semantics.
- Repair AI instructor RBAC and high-risk contract mismatches.
- Replace stale tests that currently provide false confidence.

## P1

- Complete missing frontend Phase 4 routes and flows.
- Bring AI clarification, citations, and streaming behavior up to spec.
- Make instructor jobs durable and cancellable in a meaningful way.
- Align dashboard, cancellation, and completion behavior across services.

## P2

- Improve developer ergonomics, seeding, smoke tests, and docs.
- Tighten observability claims or implement the missing capabilities.
- Expand realistic integration and E2E coverage.

## Recommended Order Of Work

1. Infra and startup hardening
2. Cross-service contract decision and refactor boundary
3. Enrollment and progress backend correctness
4. AI backend correctness
5. Frontend completion for Phase 4/5
6. Test suite rewrite around actual contracts
7. Final stack smoke tests and docs reconciliation

## Files To Execute Next

- `infrastructure-recommendations.md`
- `cross-service-contracts.md`
- `enrollment-issues.md`
- `progress-issues.md`
- `ai-student-assistant-issues.md`
- `ai-instructor-tools-issues.md`
- `frontend-phase4-5-issues.md`
- `testing-and-validation-gaps.md`
