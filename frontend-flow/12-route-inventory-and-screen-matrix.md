# Route Inventory And Screen Matrix

## Purpose

This file is the implementation-facing route inventory for the frontend flow guide.

It separates:

- current routes that already exist in `apps/web`
- target routes that should exist as the UX matures
- access rules
- owning role
- page purpose

## Route Status Legend

| Label | Meaning |
|---|---|
| Current | already present in the app |
| Evolve | present but should be reworked or expanded |
| Proposed | not present yet, recommended by this guide |

## Public Routes

| Route | Status | Access | Primary Users | Purpose |
|---|---|---|---|---|
| `/` | Proposed | public | all | restrained homepage or redirect into catalog |
| `/catalog` | Proposed | public | students, guests | public browse experience |
| `/catalog/:courseId` | Proposed | public | students, guests | public course detail and enrollment decision page |
| `/search` | Proposed | public | students, guests | query-first discovery |
| `/login` | Current | public-only | all | sign in |
| `/register` | Current | public-only | all | create account |
| `/verify-email` | Current | public-only | all | verify account |
| `/forgot-password` | Current | public-only | all | start recovery |
| `/reset-password` | Current | public-only | all | complete recovery |
| `/certificates/:certificateId` | Current | public | all | certificate verification |

## Shared Authenticated Routes

| Route | Status | Access | Primary Users | Purpose |
|---|---|---|---|---|
| `/app` | Current | authenticated | all | authenticated shell |
| `/app/profile` | Current | authenticated | all | personal account management |
| `/app/settings` | Proposed | authenticated | all | preferences and notification settings |
| `/app/notifications` | Proposed | authenticated | all | notification center |
| `/app/catalog` | Current | authenticated | all | in-app catalog browse |
| `/app/catalog/:courseId` | Current | authenticated | all | in-app course detail |
| `/app/search` | Current | authenticated | all | in-app search |

## Student Routes

| Route | Status | Access | Purpose |
|---|---|---|---|
| `/app/dashboard` | Current | student-oriented default | learning resume board |
| `/app/learning` | Current | authenticated, student-focused | enrollment list |
| `/app/learning/:enrollmentId` | Current | entitlement-based | active learning workspace |
| `/app/certificates` | Current | authenticated | certificate library |

## Instructor Routes

| Route | Status | Access | Purpose |
|---|---|---|---|
| `/app/courses` | Current | instructor or admin | course portfolio workspace |
| `/app/courses/new` | Proposed | instructor or admin | dedicated create flow |
| `/app/courses/:courseId` | Current | instructor or admin | current monolithic editor |
| `/app/courses/:courseId/overview` | Proposed | instructor or admin | metadata, status, readiness |
| `/app/courses/:courseId/curriculum` | Proposed | instructor or admin | modules and structure |
| `/app/courses/:courseId/assets` | Proposed | instructor or admin | asset operations |
| `/app/courses/:courseId/ai` | Proposed | instructor or admin | enhancement jobs and previews |
| `/app/courses/:courseId/publish` | Proposed | instructor or admin | validation, publish, version history |
| `/app/courses/:courseId/analytics` | Proposed | instructor or admin | course performance insights |

## Admin Routes

| Route | Status | Access | Purpose |
|---|---|---|---|
| `/app/admin/users` | Current | admin | user governance |
| `/app/admin/instructor-applications` | Current | admin | instructor application review |
| `/app/admin/catalog` | Proposed | admin | course governance and visibility controls |
| `/app/admin/analytics` | Proposed | admin | platform analytics |
| `/app/admin/workflows` | Proposed | admin or ops | workflow monitoring |
| `/app/admin/workflows/:workflowId` | Proposed | admin or ops | workflow detail |
| `/app/admin/dlq` | Proposed | admin or ops | dead letter queue inspection |
| `/app/admin/audit-log` | Proposed | admin or ops | audit search and traceability |
| `/app/admin/users/:userId` | Proposed | admin | user detail and audit context |

## Screen Modules Matrix

## Discovery Screens

| Screen | Must Have Modules |
|---|---|
| Catalog | search, filters, sort, results, empty state |
| Course detail | hero, outcomes, prerequisites, module preview, enrollment card |
| Search | query input, filters, result relevance feedback |

## Learning Screens

| Screen | Must Have Modules |
|---|---|
| Dashboard | continue learning, in-progress list, recent completion, notifications preview |
| My learning | enrollment list, status filter, empty state |
| Learning workspace | progress summary, module checklist, content area, assistant, completion actions |
| Certificates | certificate list, verification links |

## Authoring Screens

| Screen | Must Have Modules |
|---|---|
| Courses workspace | create CTA, drafts table/list, filters, state chips |
| Overview | metadata form, live version summary, validation summary |
| Curriculum | ordered modules, inline editing, add module, reorder |
| Assets | upload, per-module asset groups, status, item-level actions |
| AI tools | job form, streaming preview, output history, recent jobs |
| Publish | checklist, publish CTA, timeline, version history, diagnostics |
| Course analytics | learner metrics, completion, module drop-off, AI usage |

## Admin And Ops Screens

| Screen | Must Have Modules |
|---|---|
| Users | filters, dense table, role/status actions |
| Applications | status filter, application context, decision actions |
| Platform analytics | KPIs, trends, course rollups, AI health |
| Workflows | filters, workflow list, state chips, action entry points |
| Workflow detail | identifiers, step timeline, errors, retry/cancel history |
| Audit log | search filters, event list, payload detail |
| DLQ | topic filter, failure reason, replay actions |

## Route Guard Rules

| Route Type | Rule |
|---|---|
| Public-only auth pages | redirect authenticated users to default role landing |
| Authenticated shared routes | require valid session |
| Student learning routes | require entitlement or ownership of enrollment |
| Instructor routes | require `instructor` or `admin` |
| Admin routes | require `admin` |
| Ops routes | require `admin` or separate support role if later added |

## Return Path Rules

- protected public actions should carry a `from` return path to login
- successful login should honor the return path if permissions allow
- enroll actions should return the student to the specific course detail context if interrupted by auth

## Final Guidance

When implementing new routes, update this file first so the screen inventory remains the single source of truth for frontend scope.
