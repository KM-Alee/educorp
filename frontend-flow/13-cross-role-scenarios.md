# Cross-Role Scenarios

## Purpose

EduCorp is a multi-actor system. The best UX appears when screens are designed not only as isolated pages, but as linked moments across different roles.

This file captures the major cross-role scenarios the frontend should support.

## Scenario 1: Student Becomes Instructor

### Steps

1. Student signs in and visits profile.
2. Student sees instructor application card.
3. Student submits application with rationale.
4. Admin reviews the application.
5. Admin approves.
6. Student receives a notification.
7. On next sign-in, student now has instructor mode available.

### UX requirements

- profile page clearly explains the application process
- application success confirms pending state
- admin review screen exposes enough applicant context
- approval triggers visible notification and mode-switch affordance

## Scenario 2: Instructor Publishes While Students Are Enrolled

### Steps

1. Students are actively learning on READY version N.
2. Instructor updates draft for version N+1.
3. Instructor validates and publishes.
4. Publish workflow runs in the background.
5. Students continue learning on version N until N+1 becomes READY and activated.
6. Instructor sees run progress and result.

### UX requirements

- instructor publish center clearly states current live version and pending version
- student learning workspace never shows unstable content
- if activation is manual, instructor sees next action clearly
- notifications communicate publish success or failure without ambiguity

## Scenario 3: Publish Failure And Recovery

### Steps

1. Instructor triggers publish.
2. Workflow fails during extraction or indexing.
3. Instructor gets a failure notification.
4. Instructor opens publish center.
5. If needed, admin or ops user investigates workflow detail.
6. Instructor fixes draft or asset issue.
7. Instructor retries publish.

### UX requirements

- instructor gets human-readable failure summary first
- workflow detail is available for deeper diagnosis
- retry eligibility is visible
- old READY version remains clearly live during failure

## Scenario 4: Student Hits Entitlement Boundary In AI

### Steps

1. Student views a course detail page but has not enrolled.
2. Student opens assistant panel.
3. Assistant is disabled.
4. UI explains enrollment is required to unlock grounded course assistance.
5. Student enrolls.
6. Assistant becomes available inside the learning workspace.

### UX requirements

- no confusing partial AI interaction for unenrolled students
- disabled state should motivate enrollment, not look broken
- after enrollment, route student into the workspace where assistant is fully available

## Scenario 5: Course Completion And Certificate Verification

### Steps

1. Student completes final required module.
2. Course completion is confirmed.
3. Certificate record is issued.
4. Student is routed to certificate detail or certificate celebration state.
5. Student shares the public certificate link.
6. External viewer verifies the certificate.

### UX requirements

- completion moment should feel important
- certificate route must be public-safe and trust-oriented
- student certificate library should remain easy to revisit later

## Scenario 6: Admin Resolves User Escalation

### Example complaint

`I enrolled but cannot access the assistant.`

### Likely support flow

1. Admin searches for the user.
2. Admin verifies roles and account state.
3. Admin finds the course or enrollment.
4. Admin checks entitlement state.
5. Admin inspects relevant workflow or audit event if needed.

### UX requirements

- admin surfaces should be linkable across user, course, and workflow entities
- correlation IDs and entity IDs should be visible where relevant
- user detail pages should be added as the product matures

## Scenario 7: Multi-Role User Switches Context

### Example

A user is both `student` and `instructor`.

### Steps

1. User signs in.
2. Default landing opens in last-used mode.
3. User switches from Instructor mode to Student mode.
4. Navigation adapts without logging out.
5. Shared pages like profile and notifications remain stable.

### UX requirements

- explicit mode switcher
- preserve context within each mode if feasible
- avoid mixing both role nav sets at once in a confusing way

## Scenario 8: Notification-Driven Re-entry

### Example events

- instructor publish succeeded
- instructor publish failed
- student certificate issued
- admin role changed

### UX requirements

- each notification routes to the exact page needed next
- notifications summarize event, state, and action needed
- notifications should not send users to generic landing pages when a deep link is available

## Scenario 9: Admin Uses Workflow Ops Instead Of Infra UI

### Steps

1. Admin sees increased publish failures.
2. Admin opens workflow list in the product.
3. Admin filters failed workflows.
4. Admin inspects one workflow.
5. Admin identifies root step failure.
6. Admin retries if safe or coordinates with instructor.

### UX requirements

- product workflow tooling should cover the 80 percent case before Jaeger/Temporal UI is needed
- actions must be guarded and auditable

## Final Principle

Cross-role UX is where EduCorp becomes a platform rather than a collection of pages.

If a flow changes system state for one role, another role should be able to understand and act on that state without guesswork.
