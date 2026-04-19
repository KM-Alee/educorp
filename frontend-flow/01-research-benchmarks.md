# Research Benchmarks

## Why These References

EduCorp sits between three familiar product categories:

- course marketplace
- learning management system
- instructor publishing tool

No single benchmark is sufficient, so the best version of EduCorp borrows distinct patterns from each category.

## Coursera Patterns To Borrow

### What works

- strong trust signals before enrollment
- clear value framing around outcomes, difficulty, duration, and instructor credibility
- catalog and search that help users narrow quickly
- public course detail pages that answer most evaluation questions before commitment
- certificate and progress language that makes completion feel meaningful

### What EduCorp should adapt

- EduCorp should expose course value early: what you will learn, who it is for, how long it takes, prerequisites, and whether AI help is available after enrollment.
- Catalog detail pages should feel decision-ready, not like a teaser page.
- Discovery should support filtering by category, difficulty, tags, instructor, newest, and popularity as phases mature.

### What not to copy

- heavy marketing homepage composition inside the product shell
- overly promotional surfaces once the user is already signed in
- too many top-level discovery destinations that compete with learning

## Canvas Patterns To Borrow

### What works

- clear educator workflows
- modules as a first-class organizing principle
- dense, efficient teaching screens
- strong separation between learner experience and educator operations
- good use of persistent local navigation for deep course work

### What EduCorp should adapt

- the instructor experience should be module-first and operational, not decorative
- large course-editing surfaces should use stable sub-navigation and status rails
- learning workspaces should organize content, progress, and communication around the enrolled course context

### What not to copy

- institutional complexity where every screen exposes all possible configuration at once
- educator language that feels academic-only if EduCorp also serves professional learning

## Udemy Patterns To Borrow

### What works

- guided instructor publishing workflows
- checklist-driven content readiness
- curriculum builder patterns for adding lectures and course structure
- clear separation between draft work and live listing state

### What EduCorp should adapt

- publishing should feel like a guided release flow with visible stages
- instructors should always know what is missing before publish
- AI enhancements should sit near content work, not in a disconnected lab page

### What not to copy

- sprawling instructor tools with inconsistent navigation models
- over-reliance on long forms without contextual preview or status feedback

## Resulting EduCorp Product Principles

### 1. Discovery must be public-grade

The product should support a confident browsing journey even before sign-in.
That means public catalog, public course detail, and public certificate verification should exist.

### 2. Learning must be enrollment-grade

Once a student enrolls, the product must change shape.
It should stop behaving like a catalog and start behaving like a guided workspace.

### 3. Authoring must be operations-grade

Instructors are doing structured work. The UI should prioritize:

- clarity
- sequencing
- validation
- safe publish actions
- visibility into workflow state

### 4. Admin must be tooling-grade

Admin and ops screens should optimize for speed and precision, not visual novelty.

### 5. AI must be trustworthy, not magical

AI interactions should always communicate scope, evidence, and failure conditions.

## Recommended Product Shape

EduCorp should combine four UX modes:

| UX Mode | Primary Users | Pattern Source | EduCorp Expression |
|---|---|---|---|
| Discovery | Public, students | Coursera | catalog, search, course detail, public certificate verify |
| Learning | Students | Coursera + Canvas | dashboard, course workspace, progress, certificates, assistant |
| Authoring | Instructors | Canvas + Udemy | course workspace, curriculum builder, publish center, AI enhancement |
| Governance | Admin, support | SaaS admin tools + Canvas ops patterns | users, applications, analytics, workflow ops, audit log |

## UX Implications

### Navigation

- Public mode gets a lightweight top nav.
- Authenticated mode gets a role-aware app shell.
- Deep work areas get local navigation.

### State visibility

Every object with lifecycle matters should expose visible state:

- draft
- publishing
- ready
- review required
- failed
- enrolled
- completed
- verified

### Empty states

Empty states should always teach the next action:

- no enrollments -> browse catalog
- no modules -> create first module
- no publish runs -> run validation and publish
- no notifications -> explain what events appear here

### Trust language

EduCorp should consistently show:

- why an action is blocked
- what data is being used by AI
- what version is live
- what changed after publication

## Final Benchmark Summary

EduCorp should feel less like a content marketplace with a few backend features and more like a full learning operations platform with excellent student-facing discovery.

That is the lens used throughout the rest of this folder.
