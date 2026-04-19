# Page Specs: Learning And Discovery

## Catalog

### Route

`/catalog` and `/app/catalog`

### Purpose

Support browsing by filter-first exploration.

### Page anatomy

- page heading and search prompt
- filter bar
- result count and sort row
- results grid or dense list
- empty state with reset filters action

### Card contents

- title
- short description
- category
- difficulty
- duration
- instructor name later

## Search

### Route

`/search` and `/app/search`

### Purpose

Support query-first exploration.

### Key difference from catalog

Search should foreground the query box and show relevance-oriented result feedback.

## Course Detail

### Route

`/catalog/:courseId` and `/app/catalog/:courseId`

### Purpose

Turn discovery into an enrollment decision.

### Required sections

- hero summary
- enrollment card
- learning outcomes
- prerequisites
- course metadata
- module preview
- AI availability note
- related courses later

### Primary CTAs by state

- sign in to enroll
- enroll now
- open learning workspace

## Learning Dashboard

### Route

`/app/dashboard`

### Purpose

Act as the fastest return point for active students.

### Required sections

- continue learning card
- in-progress course list
- certificates summary
- recent activity
- unread notifications preview

### Anti-pattern to avoid

Do not make the dashboard a static KPI wall.

## My Learning

### Route

`/app/learning`

### Purpose

Show all enrollments with clear status and entry points.

### Required filters later

- active
- completed
- cancelled
- recently accessed

## Learning Workspace

### Route

`/app/learning/:enrollmentId`

### Purpose

Provide the primary learning environment for an enrolled course.

### Recommended page anatomy

- course header with progress
- module rail or sequenced checklist
- main content panel
- AI assistant panel or tab
- enrollment info and actions

### Required modules

- progress summary
- module completion actions
- current required modules
- completion state
- certificate callout when complete

### Future-ready enhancements

- current lesson focus state
- notes
- downloadable resources
- timeline of activity

## Certificates Index

### Route

`/app/certificates`

### Purpose

House all earned completion records.

### Required list item data

- course title
- certificate number
- issue date
- verify/view CTA

## Certificate Detail

### Route

`/certificates/:certificateId`

### Purpose

Support verification and sharing.

### Required trust elements

- verification language
- immutable identifiers
- issue date
- learner and course names

## Student Assistant Surface

### Current placement

The assistant currently appears in course detail and course pages.

### Recommended placement model

- read-only teaser on course detail when not entitled
- full assistant in learning workspace when enrolled

### Why

The assistant is most valuable after enrollment and should feel embedded in learning, not bolted onto discovery.
