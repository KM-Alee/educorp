# Interaction, Copy, And Pattern Guidelines

## Purpose

This file defines the recurring interaction patterns that make the product feel meticulous and professional.

It is not a visual style guide.
It is a behavior guide for product interactions and language.

## Product Tone

EduCorp should sound:

- calm
- precise
- instructional
- trustworthy

EduCorp should not sound:

- hype-driven
- robotic
- vague
- overly playful in high-stakes workflows

## Core Copy Rules

### Prefer explicit outcomes

Bad:

- `Saved`

Better:

- `Course details saved.`

### Prefer actionable blockers

Bad:

- `Validation failed`

Better:

- `Add at least one module before publishing.`

### Prefer system-trust language for lifecycle actions

Examples:

- `The current READY version remains live while this publish runs.`
- `Enroll to unlock tracked learning and the course assistant.`
- `This answer is grounded in course materials only.`

## CTA Patterns

### Student

- `View course`
- `Enroll now`
- `Start learning`
- `Continue learning`
- `View certificate`

### Instructor

- `Create draft`
- `Save details`
- `Add module`
- `Run validation`
- `Publish draft`
- `Retry publish`
- `Activate version`

### Admin and ops

- `Approve`
- `Reject`
- `Activate`
- `Deactivate`
- `Retry workflow`
- `Replay message`

## Confirmation Patterns

### Soft confirmation

Use for reversible or low-risk actions.

Examples:

- saving course details
- marking notification read
- submitting instructor application

### Hard confirmation

Use for destructive or privileged actions.

Examples:

- deleting draft course
- cancelling publish run
- changing admin role
- replaying DLQ message

### Confirmation content should include

- what is about to happen
- what will remain unchanged
- whether the action is reversible

## Layout Patterns

## Pattern 1: Decision page

Use for course detail.

Structure:

- title and summary
- right-side action card on desktop
- evidence sections below

## Pattern 2: Workspace page

Use for learning and authoring.

Structure:

- stable header
- context nav
- main work area
- side summary rail when useful

## Pattern 3: Dense operations page

Use for admin and ops tools.

Structure:

- filter bar
- result table
- inline actions
- expandable row detail or detail page

## Pattern 4: Timeline page

Use for publishing and workflow detail.

Structure:

- current overall status
- step timeline
- metadata panel
- available actions

## Messaging Patterns

### Validation

- group issues by severity
- link issues to the part of the product where they can be fixed
- keep warnings visually distinct from blockers

### AI clarification

Treat clarification as progress, not failure.

Good example:

- `I can help with that. Do you mean the introductory module or the optimization module?`

### AI refusal

Good example:

- `I could not find enough support for that answer in the published course materials.`

### Enrollment block

Good example:

- `This course requires completion of Intro to Statistics before enrollment.`

### Publish failure

Good example:

- `Publishing failed during asset extraction. Review unsupported files in Module 2 and retry.`

## Progress Patterns

### Student progress

- always show both percent and module count when possible
- use completion states consistently across dashboard and learning workspace

### Publishing progress

- show current step, completed steps, and pending steps
- avoid fake progress bars when actual step state is available

### Job progress

- queued and running should look distinct
- completion should preserve output and metadata

## Notification Patterns

Each notification should answer:

- what happened
- to what object
- whether action is needed
- where the user should go next

Examples:

- `Your course Intro to ML is now READY. Review and activate the new version.`
- `Publishing failed for Intro to ML during extract_text. Open the publish center to review issues.`
- `Certificate issued for Intro to ML.`

## Lists And Tables

### Lists are best for

- learning items
- catalog results
- certificates
- recent jobs when density is moderate

### Tables are best for

- admin user management
- workflow ops
- audit log
- DLQ inspection

## Microinteraction Rules

- preserve scroll position when inline edits succeed
- do not close panels after successful action unless the user is clearly done
- keep destructive actions visually separated from primary actions
- prefer inline status updates over toast-only feedback for operational pages

## Final Pattern Rule

Every important screen in EduCorp should have one dominant action and one clear state model.

If a screen feels like many unrelated widgets stitched together, it should be split or reorganized.
