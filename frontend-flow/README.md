# EduCorp Frontend Flow Guide

## Purpose

This folder defines the target frontend experience for EduCorp as a real product, not a mock shell.

It is based on:

- `prd.md`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACTS.md`
- `docs/AI_SYSTEM.md`
- `docs/FRONTEND.md`
- the existing `apps/web` routes and page components
- research patterns from Coursera, Canvas, and Udemy

The goal is to answer the practical UX questions a team needs before building:

- Who uses EduCorp?
- What does each role need to accomplish?
- What pages should exist?
- What is the default navigation model?
- What should happen before, during, and after each important action?
- How do we handle drafts, publishing, enrollment, learning, AI, analytics, and ops safely?

## Product Positioning

EduCorp is not just a course catalog and not just an LMS.

It combines:

- marketplace-style course discovery
- instructor authoring and publishing workflows
- structured learning and progress tracking
- course-scoped AI assistance with citations
- admin and internal operations tooling

That means the frontend cannot be designed like a marketing site with a few forms.
It needs a role-aware product shell with clear transitions between discovery, authoring, governance, and learning.

## Experience North Star

EduCorp should feel like:

- as trustworthy as Coursera when a learner is choosing a course
- as operational as Canvas when an educator is managing course structure
- as guided as Udemy when an instructor is preparing content for publication
- as clear as a modern SaaS product when an admin or support user is resolving problems

It should not feel like:

- a generic AI product
- a landing page stretched into an app
- a dashboard made of disconnected cards
- an over-designed, high-motion education brand site

## Design Priorities

1. Make role transitions obvious.
2. Make system state visible.
3. Protect users from invalid actions before the backend rejects them.
4. Keep high-stakes flows linear and reviewable.
5. Keep dense operational screens dense, not oversized.
6. Let students move quickly from discovery to learning.
7. Let instructors understand publish readiness at a glance.
8. Let admins and ops users trace failures without leaving the product.

## Current App vs Target Blueprint

The existing web app already covers a meaningful slice of the product:

- authentication
- profile management
- draft course creation and editing
- draft validation
- publishing status
- catalog and search
- enrollment and learning workspace
- certificates
- AI assistant and instructor enhancement panels
- admin users and instructor applications

This guide expands that into the full target experience by defining:

- public discovery entry points
- richer navigation and shell behavior
- dedicated publishing, analytics, notifications, and ops surfaces
- page-level specifications for every important route
- UX rules for edge states and role-based access

## Recommended Reading Order

1. `01-research-benchmarks.md`
2. `02-personas-and-jtbd.md`
3. `03-information-architecture.md`
4. role flow guides:
   - `04-student-flow.md`
   - `05-instructor-flow.md`
   - `06-admin-ops-flow.md`
5. page specs:
   - `07-page-specs-public-shared.md`
   - `08-page-specs-learning-discovery.md`
   - `09-page-specs-authoring-admin.md`
6. `10-state-matrix-and-ux-standards.md`
7. `11-rollout-roadmap.md`
8. `12-route-inventory-and-screen-matrix.md`
9. `13-cross-role-scenarios.md`
10. `14-interaction-copy-and-patterns.md`

## Role Matrix

| Role | Primary Goal | Core Routes | Success Signal |
|---|---|---|---|
| Student | Find, enroll, learn, complete | Catalog, course detail, dashboard, learning, certificates, AI assistant | completes courses with confidence |
| Instructor | Create, improve, publish, monitor | Course workspace, editor, publish center, AI enhancements, course analytics | publishes READY course with low friction |
| Admin | Govern users, quality, access, analytics | Users, instructor applications, catalog governance, platform analytics | resolves issues without engineering help |
| Support/Ops | Diagnose failures and replay work safely | Workflow ops, audit log, DLQ, service health | can explain and recover from failure fast |

## Route Philosophy

EduCorp should use two experience modes:

- public mode for discovery, sign-in, and certificate verification
- authenticated app mode for role-based work

Inside the app mode, the shell should adapt by role:

- student-first navigation emphasizes learning momentum
- instructor navigation emphasizes course operations
- admin navigation emphasizes governance and diagnostics

## Output of This Folder

If followed, this folder should give the team:

- a clear site map
- a role-by-role UX blueprint
- a page inventory with purpose and actions
- implementation order aligned to platform phases
- a shared language for product, design, and engineering reviews
