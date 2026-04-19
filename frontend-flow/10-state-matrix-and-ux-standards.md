# State Matrix And UX Standards

## Purpose

Great product UX is mostly state handling.
EduCorp has many stateful workflows, so the frontend must treat system state as first-class product language.

## Global State Rules

### Loading

- show skeletons for primary content regions
- keep page chrome stable during refetches
- avoid blank white screens
- for background refresh, use subtle inline pending indicators instead of full spinners

### Empty

- explain why the list is empty
- explain what the user can do next
- never use empty states that say only `No data`

### Error

- use human-readable explanation first
- preserve structured technical detail for support via correlation ID
- keep users on the page whenever retry is possible

### Success

- confirm the outcome in the same region where the action occurred
- do not overuse toasts for critical state changes that deserve persistent confirmation

## Core Object State Matrix

| Object | States | Required UI Treatment |
|---|---|---|
| Account | unverified, active, inactive | visible status chip and next action |
| Course | draft, published, archived | top-level state chip and contextual actions |
| Course version | preparing, publishing, review required, ready, failed, cancelled | timeline plus action eligibility |
| Enrollment | enrolled, completed, cancelled | progress-aware status display |
| Module progress | pending, in progress later, completed | checklist-style feedback |
| AI query | queued, streaming, clarification, refusal, completed, error | conversational state feedback with provenance |
| AI job | queued, running, completed, failed, cancelled | job history and actionable status |
| Notification | unread, read | clear visual distinction |

## Permission States

### Unauthenticated

- public pages remain usable
- protected CTAs route to sign-in with return path

### Authenticated but unauthorized

- redirect for route-level protection
- use an explanatory in-page state for action-level permissions

### Entitlement missing

This matters most for course AI and content access.

Example copy:

- `Enroll in this course to unlock the assistant and tracked learning.`

## High-Risk Action Patterns

### Destructive actions

Use confirmation for:

- delete course draft
- delete module
- delete asset
- cancel enrollment
- cancel workflow
- replay DLQ message

### Role-changing actions

Use a confirm pattern that shows:

- current access
- resulting access
- who is making the change

### Publish actions

Before publish, show:

- current validation result
- what version will remain live during processing
- whether review or activation is still required later

## AI UX Standards

### Student assistant

- always show that answers use course materials only
- citations live with the answer, not behind another click
- clarification is a valid success path, not an error
- refusal should be respectful and course-scoped

### Instructor AI

- jobs are asynchronous by default
- preview streaming is optional but useful
- output should retain course and scope context
- failed jobs must explain if the cause was rate limit, provider failure, or insufficient material

## Notification Standards

- notifications summarize an event and route to the next place of action
- unread count lives in the shell
- notification center groups by date and type
- in-app notifications should not replace persistent on-page status for critical flows

## Mobile Standards

### Student

- full support on mobile
- sticky primary actions allowed where useful
- learning workspace should collapse into tabs or sections cleanly

### Instructor

- browse and light edits on tablet and mobile
- heavy authoring is desktop-first
- publish center should remain accessible on mobile for monitoring, not deep editing

### Admin and ops

- read support on smaller screens
- action-heavy tables stay desktop-first

## Accessibility Standards

- keyboard-complete navigation for all actions
- visible focus states
- page headings must clearly describe destination
- status messages must use semantic live regions where appropriate
- color must not be the only signal for state
- tables need proper header relationships

## Error And Recovery Standards

### Include correlation ID in serious error states

This is especially important for:

- publish failures
- AI provider errors
- enrollment failures
- admin action failures

### Recovery actions should be explicit

Bad:

- `Something went wrong`

Good:

- `Publishing failed during extract_text. Review unsupported assets in Module 3 and retry.`

## Final Standard

If the user cannot answer `What state is this in?`, `Why is it blocked?`, and `What should I do next?`, the screen is not finished.
