# Admin And Ops Flow

## Admin Experience Goal

Admin users should be able to govern the platform without feeling like they are using developer tools.

## Support And Ops Goal

Support and operations users should be able to diagnose and recover common failures without leaving the product for raw infrastructure consoles unless necessary.

## Core Admin Areas

| Route | Purpose |
|---|---|
| `/app/admin/users` | manage users, roles, and active status |
| `/app/admin/instructor-applications` | review role requests |
| `/app/admin/catalog` | moderate course visibility and policy later |
| `/app/admin/analytics` | view platform metrics |
| `/app/admin/workflows` | inspect publishing and other durable workflows |
| `/app/admin/dlq` | inspect dead-lettered events |
| `/app/admin/audit-log` | trace sensitive actions |

## Flow 1: User Governance

### Main jobs

- search for a user
- verify role and status
- change role safely
- activate or deactivate access

### Required table columns

- name
- email
- roles
- verification state
- active state
- created date later if useful

### Required actions

- add/remove instructor
- add/remove admin
- activate/deactivate
- inspect audit history later

### Safety pattern

Role changes that increase privilege should show:

- current roles
- resulting roles
- who performed the action in success feedback

## Flow 2: Instructor Application Review

### Main jobs

- review pending applications
- see applicant context
- approve or reject consistently

### Page should include

- status tabs or filters
- application reasoning
- linked user context
- approval and rejection actions

### Important future enhancement

Approval should optionally show what access changes will occur.

## Flow 3: Platform Analytics

### Questions admins need answered

- How many active learners do we have?
- Are enrollments and completions trending up or down?
- Are AI systems helping or failing?
- Which courses or instructors need attention?

### Required modules

- KPI summary row
- time series charts
- top courses table
- AI usage and refusal metrics
- failure or incident indicators

## Flow 4: Workflow Ops

### Main jobs

- locate a failing publish run
- inspect step-level progress
- understand failure reason
- retry or cancel safely

### Workflow list filters

- status
- workflow type
- course id
- initiated by
- date range

### Workflow detail page should show

- workflow ID
- run ID
- entity references
- current status
- step timeline
- error detail
- prior retries
- allowed recovery actions

### UX rule

Never expose retry and cancel as unexplained buttons.
Each action should include eligibility rules and expected outcome.

## Flow 5: Audit Log

### Main jobs

- answer who changed what and when
- verify whether an admin override occurred
- support investigations with entity-level history

### Audit search filters

- actor
- action
- resource type
- resource ID
- date range
- correlation ID

### Recommended view

Dense event list with expandable payload details.

## Flow 6: DLQ And Replay

### Main jobs

- inspect failed messages
- understand why they failed
- replay safely after remediation

### Page requirements

- topic filter
- message age
- failure reason
- replay status
- replay action history

### Safety pattern

Replay should be a two-step action with a preview of the affected entity when possible.

## Flow 7: Support Triage

Support users often start from a complaint, not from a route.

Likely starting points:

- correlation ID from an error state
- certificate number
- enrollment ID
- course ID
- workflow ID
- email address

The admin experience should support jumping from those identifiers to:

- user record
- course record
- enrollment detail
- workflow detail
- audit history

## Admin And Ops Navigation Summary

### Primary admin nav

- Users
- Applications
- Catalog Governance
- Platform Analytics
- Workflows
- Audit Log
- DLQ

### Success metric

The best admin UX reduces time to confident decision.
The best ops UX reduces time to root cause.
