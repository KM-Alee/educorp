# Frontend Phase 4-5 Issues

## Scope

This file covers missing or incomplete frontend support for Phase 4 and 5 in `apps/web/src`.

## What Is Already Present

- protected/public/admin/instructor route scaffolding exists
- catalog and course detail pages exist
- student AI panel exists
- instructor enhancement panel exists
- session handling and API client foundations are present

The main gap is that the frontend still reflects a Phase 1-3 app shape with partial Phase 5 widgets, rather than a complete Phase 4/5 product flow.

## Confirmed Gaps

### 1. Phase 4 routes are missing

Evidence:

- current router in `apps/web/src/app/router.tsx:157-171`

Missing route categories:

- learning dashboard
- enrollment list/detail views
- progress-focused learning route keyed by enrollment
- certificate list/detail
- public certificate verification route if the product expects it in web

Required fix:

- add explicit Phase 4 routes and navigation entry points

### 2. Student navigation does not expose learning state

Evidence:

- header nav in `apps/web/src/app/router.tsx:70-95`

Problem:

- there is no `My Learning`, `Dashboard`, or `Certificates` entry
- student default route still biases toward catalog, not ongoing learning

Required fix:

- add navigation and adjust default student landing according to the intended product flow

### 3. There is no enrollment UX

Evidence:

- `apps/web/src/features/courses/StudentCoursePage.tsx` shows course details but no enroll flow
- no enrollment client exists in `apps/web/src/lib/api.ts`

Required fix:

- add enrollment API client methods
- add enroll CTA and status-aware UX
- surface prerequisite/capacity failures clearly from API envelopes

### 4. There is no real progress-tracking UX

Problem:

- current student course page shows modules but not enrollment-scoped progress state
- there are no module completion actions, no progress percentage, no completion state progression

Required fix:

- introduce enrollment-centric learning pages that use progress APIs directly
- distinguish catalog detail from active learner experience

### 5. Certificate UX is missing

Problem:

- no certificate list, detail, or verification pages currently exist

Required fix:

- add certificate routes, API clients, and pages

### 6. Student AI is shown without strong enrollment-aware UX

Problem:

- AI panel is mounted from catalog detail without frontend awareness of whether the user is enrolled
- backend entitlement may still block, but the UX is not coherent

Required fix:

- gate or frame AI access based on enrollment state in the UI
- if a user is not enrolled, show the correct action or explanatory state

### 7. Instructor AI panel is incomplete

Evidence:

- `apps/web/src/features/ai/AIPanels.tsx`

Missing or weak behavior:

- no streaming enhancement UX
- no cancel-job UI
- no job history/list page despite backend support
- no typed rendering for structured results

Required fix:

- complete the instructor tools UI around the actual job lifecycle and output types

### 8. Module-scope job submission can send an invalid empty string

Evidence:

- `apps/web/src/features/ai/AIPanels.tsx:241-249`

Problem:

- module scope can serialize `module_id: ''` instead of null or a valid UUID

Required fix:

- validate module selection client-side and never send empty-string IDs

### 9. Streaming AI bypasses the central auth/error pipeline

Evidence:

- manual fetch path in `apps/web/src/features/ai/AIPanels.tsx:370-429`

Problem:

- SSE requests do not reuse the API client’s token refresh and normalized error behavior

Required fix:

- implement a shared authenticated streaming helper or equivalent refresh-aware flow

### 10. AI error UX is too generic

Problem:

- current UI often discards structured API error messages and shows fallback text only

Required fix:

- preserve and display server-provided error messages where safe and useful

## Test Gaps

Current frontend tests cover basic routing/session/api mechanics, but not:

- enrollment flows
- progress flows
- certificate flows
- student AI streaming behavior
- instructor job lifecycle UX
- error handling for Phase 4/5 features

## Implementation Plan

1. Add Phase 4 route map and navigation.
2. Add enrollment and progress API client support.
3. Split catalog detail from active learning experience.
4. Add dashboard and certificate pages.
5. Harden AI panels around entitlement, errors, and streaming.
6. Add instructor job lifecycle UI.
7. Add frontend tests for all of the above.

## Exit Criteria

- students can enroll, track progress, complete modules, and view certificates via the web app
- student AI appears in the correct learning context
- instructors can run, monitor, and cancel enhancement jobs from the UI
- Phase 4 and 5 frontend flows are covered by route/component tests
