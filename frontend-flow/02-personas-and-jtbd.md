# Personas And Jobs To Be Done

## Primary Personas

## Student

### Core goals

- find a course worth taking
- understand fit before enrolling
- start learning quickly
- know exactly what is required to complete
- ask questions without leaving the course context
- earn a certificate and trust that it is real

### Main anxieties

- enrolling in the wrong course
- not knowing prerequisites or time commitment
- getting lost after enrollment
- not trusting AI answers
- not knowing whether progress is saved

### UX needs

- decision-ready course detail pages
- visible progress and completion rules
- a stable learning workspace
- citations and refusal behavior in AI responses
- frictionless resume points

### Jobs to be done

- When I browse the catalog, help me compare courses quickly.
- When I open a course detail page, answer my questions before I commit.
- When I enroll, move me directly into learning, not back into browsing.
- When I return later, show me exactly where to continue.
- When I ask the assistant a question, show me where the answer came from.

## Instructor

### Core goals

- create structured course drafts efficiently
- upload and manage assets without confusion
- know whether a draft is publish-ready
- publish safely without breaking the live course
- improve course material with AI assistance
- understand learner engagement after launch

### Main anxieties

- losing draft work
- publishing incomplete content
- not understanding why a publish failed
- AI generating low-quality or ungrounded output
- limited visibility into learner behavior

### UX needs

- a clear course workspace
- reliable autosave or obvious save affordances
- checklist-driven validation
- publish status timeline and diagnostics
- course analytics tied back to modules and outcomes

### Jobs to be done

- When I create a new course, get me from blank state to usable structure fast.
- When I edit content, keep me oriented inside the course hierarchy.
- When I publish, show me what will happen and what can go wrong.
- When a run fails, tell me exactly what to fix next.
- When I use AI tools, keep them tied to the course and version I am editing.

## Admin

### Core goals

- govern users and roles safely
- approve or reject instructor applications consistently
- monitor content and platform health
- review trends and adoption at the platform level
- resolve escalations without developer help

### Main anxieties

- accidentally granting the wrong access
- limited traceability for user changes
- unclear ownership when workflows fail
- analytics without enough context

### UX needs

- dense table-based operations
- auditability and confirmation steps
- clear filters, search, and bulk-safe patterns
- system health and workflow views

### Jobs to be done

- When I manage users, let me search, filter, and act fast.
- When I approve an instructor, show enough context to make the call.
- When the system has a failure, point me to the right diagnostic surface.
- When I view analytics, connect numbers to actionable follow-up.

## Support And Ops

### Core goals

- diagnose workflow failures quickly
- inspect DLQ and replay safely
- trace a user-reported issue by correlation ID or entity ID
- answer operational questions without opening raw infra tools first

### Main anxieties

- missing the root cause
- replaying unsafe work
- having to jump across too many systems

### UX needs

- workflow detail pages
- failure reason normalization
- audit and event timeline surfaces
- action history for manual retries and overrides

## Secondary Internal Persona: Data Analyst

### Core goals

- understand learner and course performance trends
- compare course engagement and AI usage
- trust metric definitions

### UX needs

- analytics with clear date ranges and definitions
- drill-down from platform to course
- export-friendly tables and charts

## Permission Model Summary

| Capability | Student | Instructor | Admin | Support/Ops |
|---|---|---|---|---|
| Browse READY catalog | Yes | Yes | Yes | Yes |
| Enroll | Yes | Optional if also student | Yes for testing/support only if allowed | No |
| Learn and track progress | Yes | If enrolled | Yes | No |
| Ask course AI | Yes if entitled | Yes if entitled | Yes | No |
| Create and edit drafts | No | Yes | Yes | No |
| Publish versions | No | Yes | Yes | No |
| Generate instructor AI output | No | Yes | Yes | No |
| Manage users and roles | No | No | Yes | Limited read if allowed |
| Access platform analytics | No | No | Yes | Read-only optional |
| Access workflow ops and DLQ | No | No | Yes | Yes |

## Journey Priorities

The design should prioritize user journeys in this order:

1. student discovery to enrollment
2. student resume learning and complete
3. instructor draft to publish
4. instructor publish failure recovery
5. student AI question with trustworthy citation
6. admin user and instructor application governance
7. support workflow diagnosis and replay

If any screen or flow does not help one of these journeys, it should not become a top-level navigation destination.
