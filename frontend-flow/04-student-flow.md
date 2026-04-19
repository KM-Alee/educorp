# Student Flow

## Student Experience Goal

The student experience should answer one question at every step:

`What should I do next to make progress?`

Students should never feel dropped into a raw list of routes or disconnected data screens.

## Student Lifecycle

```text
Discover -> Evaluate -> Enroll -> Start learning -> Resume learning -> Ask AI -> Complete -> Verify/share certificate
```

## Entry Points

Students can enter from:

- public catalog
- public search
- direct course detail link
- sign-in return path
- notification that links back into a course or certificate

## Core Student Pages

| Route | Purpose | Lifecycle Stage |
|---|---|---|
| `/catalog` or `/app/catalog` | browse courses | discover |
| `/catalog/:courseId` or `/app/catalog/:courseId` | evaluate a course | evaluate |
| `/app/dashboard` | resume and overview | return state |
| `/app/learning` | all enrollments | manage |
| `/app/learning/:enrollmentId` | active course workspace | learn |
| `/app/certificates` | earned outcomes | complete |
| `/certificates/:certificateId` | public verification | share |
| `/app/notifications` | event inbox | ongoing |

## Flow 1: Discover

### Goal

Help students narrow quickly without sign-in pressure.

### Page model

Catalog should prioritize:

- search bar
- category and difficulty filters
- tag filters
- sort controls
- course cards with trust metadata

### Required card data

- title
- short description
- instructor name when available
- category
- difficulty
- estimated duration
- readiness/public preview signal

### Primary CTA

- `View course`

### Secondary CTA

- save/bookmark later if implemented

## Flow 2: Evaluate Course

### Goal

Give the student enough confidence to decide whether to enroll.

### Course detail sections

- hero summary
- what you will learn
- prerequisites
- course structure preview
- module list
- estimated duration and difficulty
- instructor attribution
- public preview note if available
- enrollment card

### Decision states

| State | UI behavior |
|---|---|
| not signed in | show sign-in-aware enrollment CTA |
| signed in, not enrolled | show `Enroll now` |
| enrolled | show `Open learning workspace` |
| prerequisites unmet | explain why and link to missing path later |
| course full | explain capacity state and waitlist later if added |

### Important UX rule

The student should understand before clicking enroll:

- what they get access to
- how progress works
- whether AI help unlocks after enrollment

## Flow 3: Enroll

### Desired behavior

Enrollment should feel instant and safe.

### Success pattern

After successful enrollment:

- show a lightweight success state
- confirm course access is unlocked
- immediately offer `Start learning`
- optionally show `Return to dashboard`

### Failure pattern

If enrollment fails, keep the student on the course detail page and explain:

- prerequisite block
- capacity block
- auth/session expiration
- duplicate enrollment resolution

## Flow 4: Start Learning

### Goal

Turn a catalog object into a focused workspace.

### Learning workspace anatomy

- course header with progress summary
- module checklist or sequence rail
- primary content pane
- assistant panel or assistant tab
- enrollment metadata and actions

### What students need most on first open

- a clear start point
- visible completion rules
- progress percentage
- module completion buttons or progress trackers
- reassurance that progress saves

## Flow 5: Resume Learning

### Dashboard behavior

Dashboard should not be a generic analytics page.
It should act like a resume board.

### Top content priority

1. resume current course
2. recent activity
3. outstanding required modules
4. newly available certificates
5. notifications affecting active learning

### Key cards

- `Continue where you left off`
- `In progress`
- `Recently completed`
- `Certificates`
- `Unread notifications`

## Flow 6: Ask AI

### Goal

Provide grounded help inside the course context.

### Student assistant rules

- assistant only appears as active when entitlement exists
- module scoping is optional but easy to use
- streaming is the default premium interaction
- citations are not optional UI garnish; they are part of the answer

### Required UI elements

- question input
- optional module scope
- streaming answer area
- citation cards
- clarification prompt handling
- refusal state with course-scoped explanation

### Trust language

Always remind the learner that the assistant answers from course materials only.

### Bad AI experience to avoid

- generic chatbot chrome
- no provenance
- making the user guess whether the answer is grounded

## Flow 7: Complete Course

### Goal

Completion should feel earned and obvious.

### Required completion moments

- final module completion feedback
- course completion confirmation
- certificate issuance confirmation
- next CTA: view certificate, continue learning, browse catalog

### Certificate page should show

- course title
- learner name
- certificate number
- issuance time
- verification route

## Flow 8: Return And Share

Students often come back after completion for proof, not more learning.

The product should make it easy to:

- view all certificates
- verify one publicly
- return to catalog for next course

## Student Navigation Summary

### Primary student destinations

- Dashboard
- My Learning
- Catalog
- Search
- Certificates
- Notifications
- Profile

### Student success metric

The best student UX reduces time from sign-in to meaningful learning action.

That means:

- fewer dead-end pages
- fewer repeated search steps
- stronger resume affordances
- better clarity around completion
