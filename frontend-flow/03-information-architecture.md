# Information Architecture

## IA Goals

- keep discovery easy for public users
- keep role transitions obvious after sign-in
- keep deep work areas stable and predictable
- reduce top-level clutter by using context-specific sub-navigation

## High-Level Site Map

```text
Public
|- /
|- /catalog
|- /catalog/:courseId
|- /search
|- /login
|- /register
|- /verify-email
|- /forgot-password
|- /reset-password
|- /certificates/:certificateId

Authenticated App
|- /app
   |- /app/dashboard
   |- /app/learning
   |- /app/learning/:enrollmentId
   |- /app/certificates
   |- /app/catalog
   |- /app/catalog/:courseId
   |- /app/search
   |- /app/notifications
   |- /app/profile
   |- /app/settings
   |- /app/courses
   |- /app/courses/new
   |- /app/courses/:courseId/overview
   |- /app/courses/:courseId/curriculum
   |- /app/courses/:courseId/assets
   |- /app/courses/:courseId/ai
   |- /app/courses/:courseId/publish
   |- /app/courses/:courseId/analytics
   |- /app/admin/users
   |- /app/admin/instructor-applications
   |- /app/admin/catalog
   |- /app/admin/analytics
   |- /app/admin/workflows
   |- /app/admin/dlq
   |- /app/admin/audit-log
```

## Existing Route Coverage

| Route | Current App | Keep | Evolve |
|---|---|---|---|
| `/login` and auth routes | Yes | Yes | polish |
| `/app/profile` | Yes | Yes | expand with settings and notifications |
| `/app/catalog` | Yes | Yes | make public too |
| `/app/catalog/:courseId` | Yes | Yes | expand detail depth |
| `/app/search` | Yes | Yes | unify with public search |
| `/app/dashboard` | Yes | Yes | add resume and alerts |
| `/app/learning` | Yes | Yes | add filters and sort |
| `/app/learning/:enrollmentId` | Yes | Yes | expand to true course workspace |
| `/app/certificates` | Yes | Yes | add share and verification affordances |
| `/app/courses` | Yes | Yes | split list/new/create flows |
| `/app/courses/:courseId` | Yes | Yes | split into sub-routes |
| `/app/admin/users` | Yes | Yes | add audit context |
| `/app/admin/instructor-applications` | Yes | Yes | add richer review context |
| notifications | No | Add | Phase 6 |
| analytics pages | No | Add | Phase 6 |
| workflow ops pages | No | Add | Phase 7 |

## Navigation Model

## Public Navigation

Public mode should use a slim top navigation:

- logo
- Catalog
- Search
- Sign in
- Create account

If a public homepage exists, it should funnel users toward discovery or sign-in, not act as a full marketing site.

## Authenticated Global Navigation

The authenticated shell should use a global top bar plus optional left-side context nav.

### Global top bar content

- logo and home shortcut
- primary product destinations
- global search entry
- notifications bell
- profile menu

### Student primary nav

- Dashboard
- My Learning
- Catalog
- Search
- Certificates
- Notifications
- Profile

### Instructor primary nav

- Courses
- Catalog
- Search
- Notifications
- Profile

### Admin primary nav

- Users
- Applications
- Catalog Governance
- Platform Analytics
- Workflows
- Notifications
- Profile

## Context Navigation

Deep areas should use local nav instead of adding more global destinations.

### Learning workspace local nav

- Overview
- Modules
- AI Assistant
- Notes or resources later if added
- Certificate when completed

### Course authoring local nav

- Overview
- Curriculum
- Assets
- AI Tools
- Publish
- Analytics

### Admin local nav

- Users
- Applications
- Catalog Governance
- Platform Analytics
- Workflow Ops
- Audit Log
- DLQ

## Default Landings By Role

| Role mix | Default route |
|---|---|
| student only | `/app/dashboard` |
| instructor only | `/app/courses` |
| admin only | `/app/admin/users` |
| instructor + student | `/app/courses` with quick switch to dashboard |
| admin + instructor | `/app/admin/users` with pinned switch to courses |

## Role Switching

Users with multiple roles should not be forced into one blended navigation forever.

Recommended pattern:

- keep one shared shell
- expose a visible mode switcher: `Student`, `Instructor`, `Admin`
- persist last used mode locally
- preserve access to shared pages like profile and notifications in all modes

## Search Entry Points

EduCorp has three search intents and should not collapse them into one ambiguous page.

| Search Type | User Intent | Surface |
|---|---|---|
| Catalog search | find courses | public and app search page |
| In-course AI retrieval | ask questions about course content | learning and course detail assistant panels |
| Admin search | find users, workflows, audit entries | within admin pages with scoped filters |

## Breadcrumb Rules

Use breadcrumbs for deep routes only.

Examples:

- `Catalog / Intro to ML`
- `Courses / Intro to ML / Publish`
- `Admin / Workflows / publish-1234`
- `My Learning / Enrollment 47ac89f1`

## Responsive Rules

- Student flows must work fully on mobile.
- Catalog and learning should collapse to stacked layouts cleanly.
- Instructor authoring should support tablet and desktop first.
- Admin and ops tools should be usable on tablet but optimized for desktop.

## IA Summary

The right IA for EduCorp is not one flat app shell.
It is a public discovery layer plus a role-aware operations layer.

That distinction should drive route design, navigation, and page hierarchy from the start.
