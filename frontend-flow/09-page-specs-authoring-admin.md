# Page Specs: Authoring And Admin

## Courses Workspace

### Route

`/app/courses`

### Purpose

Act as the instructor home base.

### Required sections

- create new course CTA
- drafts list
- published courses list later
- filters
- course state chips
- quick resume editing

### Key improvement over current screen

Separate `create new course` from `manage existing courses` more clearly.

## New Course

### Route

`/app/courses/new`

### Purpose

Provide a focused creation step instead of crowding the workspace.

### Required fields

- title
- short description
- category
- difficulty
- estimated duration
- tags

## Course Overview

### Route

`/app/courses/:courseId/overview`

### Purpose

Show course metadata, status, and readiness summary.

### Required sections

- course details form
- course status chips
- last updated
- live version summary
- validation summary

## Curriculum

### Route

`/app/courses/:courseId/curriculum`

### Purpose

Manage modules and structure.

### Required sections

- add module action
- ordered module list
- module inline edit
- reorder controls
- required toggle
- per-module asset counts

## Assets

### Route

`/app/courses/:courseId/assets`

### Purpose

Centralize file operations.

### Required sections

- upload area
- grouped assets by module
- type and status labels
- validation feedback
- download and delete actions

## AI Tools

### Route

`/app/courses/:courseId/ai`

### Purpose

Give instructors a dedicated surface for enhancement work.

### Required sections

- job creation form
- streaming preview area
- recent jobs
- output history
- provenance context

## Publish Center

### Route

`/app/courses/:courseId/publish`

### Purpose

Control release readiness and workflow status.

### Required sections

- validation checklist
- publish CTA
- current live version
- current pending run
- step timeline
- review and activation actions
- version history

### This page is critical

It should feel like a release center, not just another card in the editor.

## Course Analytics

### Route

`/app/courses/:courseId/analytics`

### Purpose

Show how the course performs after publication.

### Required sections

- enrollments
- completion rate
- active learners
- module-level breakdown
- AI usage in this course

## Admin Users

### Route

`/app/admin/users`

### Purpose

Manage access safely.

### Required sections

- search and filters
- dense user table
- role action buttons
- status action buttons
- inline success and error feedback

## Instructor Applications

### Route

`/app/admin/instructor-applications`

### Purpose

Review requests consistently.

### Required sections

- status filter
- application list
- applicant context
- approve and reject actions

## Platform Analytics

### Route

`/app/admin/analytics`

### Purpose

Monitor platform-level health and growth.

### Required sections

- KPI row
- enrollment trends
- completion trends
- AI system metrics
- top courses and risk indicators

## Workflow Ops

### Route

`/app/admin/workflows`

### Purpose

Inspect and act on durable workflows.

### Required sections

- filterable workflow table
- state chips
- workflow detail drawer or page
- retry and cancel affordances

## DLQ

### Route

`/app/admin/dlq`

### Purpose

Expose failed event messages for safe replay.

## Audit Log

### Route

`/app/admin/audit-log`

### Purpose

Make sensitive actions traceable.

### Required sections

- search filters
- event list
- payload preview
- correlation ID display

## Support Detail Views

Recommended future detail routes:

- `/app/admin/workflows/:workflowId`
- `/app/admin/users/:userId`
- `/app/admin/courses/:courseId`

These views make investigations much faster than table-only admin tools.
