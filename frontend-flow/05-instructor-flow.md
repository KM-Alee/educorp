# Instructor Flow

## Instructor Experience Goal

The instructor experience should feel like a calm publishing system.

The instructor always needs to know:

- what course they are editing
- what state the course is in
- what is missing before publish
- what version is live now
- what happened in the last publish run

## Instructor Lifecycle

```text
Become instructor -> Create draft -> Structure curriculum -> Upload assets -> Enrich content -> Validate -> Publish -> Review live status -> Improve course -> Monitor analytics
```

## Entry Points

Instructors enter through:

- default courses workspace
- direct deep link into a specific course
- notification about publish success or failure
- admin-approved instructor status change

## Core Instructor Pages

| Route | Purpose |
|---|---|
| `/app/courses` | portfolio workspace for all owned courses |
| `/app/courses/new` | fast create flow |
| `/app/courses/:courseId/overview` | course metadata and readiness summary |
| `/app/courses/:courseId/curriculum` | modules and structure editing |
| `/app/courses/:courseId/assets` | asset upload and management |
| `/app/courses/:courseId/ai` | enhancement jobs and previews |
| `/app/courses/:courseId/publish` | validation, publish history, run detail |
| `/app/courses/:courseId/analytics` | learner and AI usage insights |

## Flow 1: Become Instructor

### Student-to-instructor transition

For non-instructor users, the profile page should offer:

- explanation of instructor access
- application form
- expected review time
- application status after submission

### After approval

The first instructor sign-in should show a focused welcome state:

- `Create your first course`
- link to sample course structure guidance
- brief explanation of draft vs published states

## Flow 2: Create Draft

### Goal

Get from zero to a structured course shell in under two minutes.

### Preferred create pattern

Use a short create flow with essential fields only:

- title
- short description
- category
- difficulty
- estimated duration
- tags

Everything else can be completed inside the course overview.

### Success behavior

After creation, send the instructor directly to the new course overview or curriculum tab.

## Flow 3: Structure Curriculum

### Goal

Make the course outline easy to read and easy to change.

### Curriculum builder requirements

- visible module order
- add module quickly
- edit inline without losing orientation
- reorder safely
- mark required vs optional
- show asset counts per module

### Recommended pattern

The curriculum page should behave like a board or structured list, not like a disconnected form stack.

## Flow 4: Upload And Manage Assets

### Goal

Reduce uncertainty around what has been uploaded and what will be published.

### Asset page should show

- grouped by module
- asset type and file name
- upload status
- size and validation feedback
- download link
- delete action only while draft is editable

### Important UX rule

Uploads should report success at the item level, not only at the page level.

## Flow 5: Enrich Content With AI

### Goal

Make AI a content helper, not a separate product.

### AI tools should support

- summary generation
- learning objectives
- quiz generation
- glossary generation
- scope by course or module

### Required affordances

- explicit scope
- parameter controls
- queued job view
- streaming preview mode
- result provenance tied to course and version context

### UX warning

Do not hide AI output inside a modal that disappears.
Outputs should be reviewable, comparable, and savable into course content later.

## Flow 6: Validate Draft

### Goal

Tell the instructor whether the draft is publishable and why.

### Validation panel must answer

- Is the course valid right now?
- What errors block publish?
- What warnings are advisory only?
- Which tab should the instructor visit to fix each issue?

### Best pattern

Checklist grouped by category:

- metadata
- curriculum
- assets
- publish safety

## Flow 7: Publish

### Goal

Make a complex backend workflow feel understandable and safe.

### Publish center sections

- current live version summary
- pre-publish checklist
- publish CTA
- in-progress run timeline
- step-level status
- failure diagnostics
- review and activation state
- version history

### Publish success behavior

After publish starts:

- keep the instructor in the publish center
- show a running timeline
- allow safe exit while preserving status via notifications

### Publish failure behavior

Show:

- failed step
- human-readable explanation
- assets or modules involved
- recommended next action
- retry CTA if safe

### Critical trust rule

Always communicate that the previous READY version stays live until the new version is safe.

## Flow 8: Review And Activate

If the workflow requires approval or manual activation:

- surface the approval state prominently
- explain who can approve
- show activation CTA only when valid
- make the live version and pending version visually distinct

## Flow 9: Monitor Course Performance

### Course analytics should answer

- Are learners enrolling?
- Are they completing?
- Where do they stall?
- What are they asking the AI assistant?

### Minimum analytics modules

- enrollments over time
- active learners
- completion rate
- module drop-off
- AI queries and answer rate

## Instructor Navigation Summary

### Global

- Courses
- Catalog
- Search
- Notifications
- Profile

### Local inside a course

- Overview
- Curriculum
- Assets
- AI Tools
- Publish
- Analytics

### Instructor success metric

The best instructor UX reduces uncertainty more than it reduces clicks.

If the instructor always knows course state, publish state, and next fix, the product will feel professional.
