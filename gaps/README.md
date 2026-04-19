# Phase 4-5 Gap Dossier

## Purpose

This folder is a remediation dossier for the current Phase 4 and Phase 5 implementation state in EduCorp. It is written for a capable implementation agent that will execute the fixes in order, not for passive documentation only.

The goal is to close the gap between `docs/PHASES.md` and the code that currently exists across:

- `services/enrollment`
- `services/progress`
- `services/ai`
- `apps/web`
- supporting infrastructure, startup, and test tooling

## Audit Method

This dossier was produced by comparing Phase 4 and 5 requirements in `docs/PHASES.md` against the current repository implementation, supported by direct file inspection and focused sub-audits of:

- enrollment and progress backends
- AI backend
- frontend Phase 4/5 routes and UI
- infra, startup, and test support

## How To Use This Folder

Execute these files in order. Do not skip the early architectural and infra items, because several later features are currently implemented on top of unstable or contradictory foundations.

1. `00-overall-gap-map.md`
2. `infrastructure-recommendations.md`
3. `cross-service-contracts.md`
4. `enrollment-issues.md`
5. `progress-issues.md`
6. `ai-student-assistant-issues.md`
7. `ai-instructor-tools-issues.md`
8. `frontend-phase4-5-issues.md`
9. `testing-and-validation-gaps.md`

## Global Findings

- Phase 4 and 5 are partially implemented, not absent.
- The main problem is not lack of code volume; it is correctness, consistency, and end-to-end integrity.
- Several flows appear to work in isolation but are backed by stale tests, cross-schema shortcuts, shallow readiness checks, and missing frontend coverage.
- Some endpoints exist but do not satisfy the intended contract in `docs/PHASES.md`.

## Required Execution Mindset

- Prefer contract correctness over preserving local shortcuts.
- Preserve the service boundaries described in project guidance unless there is an explicit documented exception.
- Convert pseudo-working flows into verifiably working flows with real persistence, real tests, and real startup validation.
- When a fix exposes a deeper architectural contradiction, resolve the contradiction instead of layering more patches on top.
