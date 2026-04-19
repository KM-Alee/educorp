# Rollout Roadmap

## Purpose

This roadmap turns the flow guide into an implementation sequence aligned to EduCorp's backend phases.

## Current Frontend Baseline

The app already contains the foundations of:

- auth
- profile
- catalog and search
- learning dashboard and enrollment workspace
- course authoring
- publishing status
- AI panels
- admin user and application screens

That means the next step is not to restart the frontend.
It is to reorganize and deepen it so the experience feels intentional.

## Recommended Build Order

## Phase A: Shell And IA Cleanup

### Goal

Turn the current route set into a clear product shell.

### Work

- add public catalog and public course detail routes
- introduce role mode switching for multi-role users
- add notifications entry point in shell
- split `/app/courses/:courseId` into local sub-routes
- formalize breadcrumbs and context nav

## Phase B: Student Experience Polish

### Goal

Make discovery and learning feel continuous.

### Work

- improve course detail with stronger decision support
- upgrade dashboard into resume-first experience
- deepen learning workspace structure
- move full assistant emphasis into enrolled learning context
- expand certificate flows and share states

## Phase C: Instructor Workspace Refactor

### Goal

Move from a single long editor page to a professional course workspace.

### Work

- add course overview, curriculum, assets, AI, publish, analytics tabs
- add dedicated new-course route
- create publish center with version history and clearer step states
- separate AI enhancements into dedicated page

## Phase D: Phase 6 Product Surfaces

### Goal

Complete the user-facing product with notifications and analytics.

### Work

- notifications center
- notification preferences in settings
- course analytics for instructors
- platform analytics for admins

## Phase E: Phase 7 Admin And Ops Surfaces

### Goal

Turn internal operations into first-class product tools.

### Work

- workflow ops list and detail pages
- audit log UI
- DLQ inspection and replay UI
- richer user detail pages

## Recommended UX Milestones

| Milestone | Outcome |
|---|---|
| M1 | clear public vs authenticated IA |
| M2 | student can browse, enroll, learn, and complete through a polished path |
| M3 | instructor can create, validate, publish, and monitor through a dedicated workspace |
| M4 | notifications and analytics complete the product loop |
| M5 | admin and ops users can govern and recover failures confidently |

## What Should Change In The Existing Frontend First

1. Extract the current monolithic course editor into route-based sections.
2. Introduce notifications and settings in the shell structure even if content starts thin.
3. Add a public catalog path so the product is discoverable before sign-in.
4. Reframe the dashboard around student resume behavior.
5. Create a dedicated publish center instead of keeping publish controls buried in the editor.

## Definition Of Done For The Frontend Flow Work

The frontend should be considered aligned with this guide when:

- every role has a coherent home and task flow
- every major API-backed lifecycle has a dedicated UX surface
- every key state has an intentional presentation and next action
- public discovery and authenticated operations feel like one product, not two unrelated apps

## Final Recommendation

Treat this folder as a product blueprint and review it whenever new routes or major screens are introduced.

If a new page does not fit one of these flows, update the flow guide before implementation.
