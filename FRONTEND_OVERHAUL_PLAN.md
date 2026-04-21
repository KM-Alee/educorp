# EduCorp — Frontend Overhaul Implementation Plan

> **Goal**: Transform the existing functional frontend into a polished, human-crafted, role-separated application with a cream/black/white design system — without changing any backend APIs.

---

## Part 1 — Understanding Phase

### 1.1 Backend & API Mapping

The backend exposes **9 services** through Traefik at `/api/v1/*`. The existing `lib/api.ts` already wraps **70+ API functions** with proper TypeScript types, error handling, and token refresh. This layer is **complete and will not be rewritten** — only extended if missing endpoints surface.

**API → Feature Mapping:**

| Service | Frontend Feature Area | Key Endpoints Used |
|---------|----------------------|-------------------|
| Auth (`/auth/*`) | Login, Register, Verify, Reset, Profile | register, login, refresh, me, forgot/reset-password |
| Admin (`/admin/*`) | Admin Dashboard | users CRUD, instructor-applications, audit-log, workflows, DLQ |
| Course (`/courses/*`) | Instructor Workspace, Catalog | CRUD courses, modules, assets, draft-content, validate |
| Publishing (`/publishing/*`) | Publish Center | versions, retry, cancel, activate |
| Enrollment (`/enrollments/*`) | Student Enrollment | enroll, list, cancel, enrollment-status |
| Progress (`/progress/*`) | Learning Workspace | dashboard, enrollment progress, module complete, certificates |
| Search (`/search/*`) | Catalog & Discovery | keyword search with filters |
| AI (`/ai/*`) | AI Assistant & Instructor Tools | ask, ask/stream, clarify, instructor/enhance, jobs |
| Notifications (`/notifications/*`) | Notification Center | list, mark-read, read-all |
| Analytics (`/analytics/*`) | Admin & Instructor Analytics | platform metrics, course metrics |

### 1.2 Current Frontend State Assessment

**What exists and works:**
- Complete API client layer (70+ functions, types, SSE streaming, error handling)
- Session management with token refresh
- Role-based route guards
- All feature directories present with functional pages
- React Query integration for data fetching

**What needs the overhaul:**
- All pages are built as monolithic single-file components (some files are 1000+ lines)
- Design is functional but lacks the cream/black/white editorial feel
- No proper component decomposition — pages inline all UI
- No shared design system components
- Navigation feels generic, not role-optimized
- Dense data screens (admin tables, course editor) need layout refinement
- Mobile responsiveness is minimal
- State handling (empty, loading, error) is inconsistent

---

## Part 2 — Frontend Architecture Plan

### 2.1 New Directory Structure

```
apps/web/src/
├── app/
│   ├── router.tsx                 # Route definitions (refactored)
│   ├── providers.tsx              # QueryClient, Router, Theme providers
│   └── layouts/
│       ├── PublicLayout.tsx        # Slim top nav for public pages
│       ├── AuthLayout.tsx          # Centered card layout for auth forms
│       ├── AppShell.tsx            # Authenticated shell with sidebar + topbar
│       └── AdminShell.tsx          # Admin sub-layout with admin nav
│
├── components/                    # Shared design system components
│   ├── ui/                        # Primitives
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Textarea.tsx
│   │   ├── Badge.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── ConfirmDialog.tsx
│   │   ├── Skeleton.tsx
│   │   ├── Spinner.tsx
│   │   ├── EmptyState.tsx
│   │   ├── ErrorState.tsx
│   │   ├── Avatar.tsx
│   │   └── Tooltip.tsx
│   ├── data/                      # Data display
│   │   ├── DataTable.tsx           # Sortable, filterable table
│   │   ├── FilterBar.tsx
│   │   ├── Pagination.tsx
│   │   ├── StatCard.tsx
│   │   ├── StatRow.tsx
│   │   ├── Timeline.tsx
│   │   └── ProgressBar.tsx
│   ├── feedback/                  # Feedback & messages
│   │   ├── Toast.tsx
│   │   ├── Banner.tsx
│   │   └── StatusChip.tsx
│   ├── navigation/                # Navigation
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   ├── Breadcrumbs.tsx
│   │   ├── TabNav.tsx
│   │   └── NotificationBell.tsx
│   └── form/                      # Form composites
│       ├── FormField.tsx
│       ├── FormStack.tsx
│       ├── SearchInput.tsx
│       └── FileUpload.tsx
│
├── features/                      # Feature modules (refactored)
│   ├── auth/
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── VerifyEmailPage.tsx
│   │   │   ├── ForgotPasswordPage.tsx
│   │   │   └── ResetPasswordPage.tsx
│   │   └── components/
│   │       └── AuthCard.tsx
│   │
│   ├── student/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── LearningPage.tsx
│   │   │   ├── LearningWorkspacePage.tsx
│   │   │   ├── CertificatesPage.tsx
│   │   │   └── CertificateDetailPage.tsx
│   │   └── components/
│   │       ├── ContinueLearningCard.tsx
│   │       ├── EnrollmentCard.tsx
│   │       ├── ModuleChecklist.tsx
│   │       ├── ProgressRing.tsx
│   │       └── CertificateCard.tsx
│   │
│   ├── catalog/
│   │   ├── pages/
│   │   │   ├── CatalogPage.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   └── CourseDetailPage.tsx
│   │   └── components/
│   │       ├── CourseCard.tsx
│   │       ├── CourseHero.tsx
│   │       ├── EnrollmentDecisionCard.tsx
│   │       ├── ModulePreview.tsx
│   │       └── CatalogFilters.tsx
│   │
│   ├── instructor/
│   │   ├── pages/
│   │   │   ├── CoursesWorkspacePage.tsx
│   │   │   ├── CreateCoursePage.tsx
│   │   │   ├── CourseOverviewPage.tsx
│   │   │   ├── CurriculumPage.tsx
│   │   │   ├── AssetsPage.tsx
│   │   │   ├── AIToolsPage.tsx
│   │   │   ├── PublishPage.tsx
│   │   │   └── CourseAnalyticsPage.tsx
│   │   └── components/
│   │       ├── CourseListItem.tsx
│   │       ├── ModuleEditor.tsx
│   │       ├── ModuleReorder.tsx
│   │       ├── AssetUploader.tsx
│   │       ├── AssetRow.tsx
│   │       ├── ValidationPanel.tsx
│   │       ├── PublishTimeline.tsx
│   │       ├── VersionHistory.tsx
│   │       ├── AIJobCard.tsx
│   │       └── CourseTabNav.tsx
│   │
│   ├── admin/
│   │   ├── pages/
│   │   │   ├── UsersPage.tsx
│   │   │   ├── ApplicationsPage.tsx
│   │   │   ├── PlatformAnalyticsPage.tsx
│   │   │   ├── WorkflowsPage.tsx
│   │   │   ├── WorkflowDetailPage.tsx
│   │   │   ├── AuditLogPage.tsx
│   │   │   └── DLQPage.tsx
│   │   └── components/
│   │       ├── UserRow.tsx
│   │       ├── RoleManager.tsx
│   │       ├── ApplicationReviewCard.tsx
│   │       ├── AnalyticsKPIRow.tsx
│   │       ├── WorkflowStepTimeline.tsx
│   │       └── DLQMessageCard.tsx
│   │
│   ├── notifications/
│   │   ├── pages/
│   │   │   └── NotificationsPage.tsx
│   │   └── components/
│   │       ├── NotificationItem.tsx
│   │       └── NotificationFilters.tsx
│   │
│   ├── ai/
│   │   └── components/
│   │       ├── AIAssistantPanel.tsx
│   │       ├── AIChatMessage.tsx
│   │       ├── AICitation.tsx
│   │       ├── AIEnhancementPanel.tsx
│   │       └── AIJobStatus.tsx
│   │
│   ├── profile/
│   │   ├── pages/
│   │   │   └── ProfilePage.tsx
│   │   └── components/
│   │       ├── ProfileForm.tsx
│   │       └── InstructorApplicationForm.tsx
│   │
│   └── settings/
│       └── pages/
│           └── SettingsPage.tsx
│
├── hooks/                         # Shared hooks
│   ├── useAuth.ts
│   ├── usePagination.ts
│   ├── useDebounce.ts
│   ├── useMediaQuery.ts
│   └── useNotifications.ts
│
├── lib/                           # Untouched — existing API layer
│   ├── api.ts
│   ├── session.ts
│   └── types.ts
│
├── styles/
│   ├── tokens.css                 # Design tokens (colors, spacing, typography)
│   ├── reset.css                  # CSS reset
│   ├── utilities.css              # Utility classes
│   └── components.css             # Component-level styles
│
└── index.css                      # Import orchestrator
```

### 2.2 Routing Structure

```
PUBLIC ROUTES (PublicLayout)
├── /                              → HomePage (restrained landing)
├── /catalog                       → CatalogPage
├── /catalog/:courseId              → CourseDetailPage
├── /search                        → SearchPage
└── /certificates/:certificateId   → CertificateDetailPage

AUTH ROUTES (AuthLayout)
├── /login                         → LoginPage
├── /register                      → RegisterPage
├── /verify-email                  → VerifyEmailPage
├── /forgot-password               → ForgotPasswordPage
└── /reset-password                → ResetPasswordPage

APP ROUTES (AppShell — authenticated)
├── /app                           → Redirect by role
│
├── STUDENT ROUTES
│   ├── /app/dashboard             → DashboardPage
│   ├── /app/learning              → LearningPage
│   ├── /app/learning/:enrollmentId → LearningWorkspacePage
│   └── /app/certificates          → CertificatesPage
│
├── SHARED ROUTES
│   ├── /app/catalog               → CatalogPage
│   ├── /app/catalog/:courseId      → CourseDetailPage
│   ├── /app/search                → SearchPage
│   ├── /app/notifications         → NotificationsPage
│   ├── /app/profile               → ProfilePage
│   └── /app/settings              → SettingsPage
│
├── INSTRUCTOR ROUTES (instructor/admin guard)
│   ├── /app/courses               → CoursesWorkspacePage
│   ├── /app/courses/new           → CreateCoursePage
│   └── /app/courses/:courseId     → CourseLayout (with tab nav)
│       ├── /overview              → CourseOverviewPage
│       ├── /curriculum            → CurriculumPage
│       ├── /assets                → AssetsPage
│       ├── /ai                    → AIToolsPage
│       ├── /publish               → PublishPage
│       └── /analytics             → CourseAnalyticsPage
│
└── ADMIN ROUTES (admin guard — AdminShell)
    ├── /app/admin/users           → UsersPage
    ├── /app/admin/instructor-applications → ApplicationsPage
    ├── /app/admin/analytics       → PlatformAnalyticsPage
    ├── /app/admin/workflows       → WorkflowsPage
    ├── /app/admin/workflows/:id   → WorkflowDetailPage
    ├── /app/admin/audit-log       → AuditLogPage
    └── /app/admin/dlq             → DLQPage
```

### 2.3 Component Hierarchy

```
App
├── Providers (QueryClient, Router)
│
├── PublicLayout
│   ├── TopBar (logo, Catalog, Search, Sign in, Create account)
│   └── <Outlet />
│
├── AuthLayout
│   └── AuthCard
│       └── <form />
│
└── AppShell
    ├── TopBar (logo, search, NotificationBell, Avatar menu)
    ├── Sidebar (role-aware navigation links)
    └── Main content area
        └── <Outlet />
            ├── Page header (Breadcrumbs, title, actions)
            └── Page body
```

---

## Part 3 — Design System

### 3.1 Color System: Cream / Black / White

The design replaces the existing burnt-orange accent system with a warm, editorial palette that feels handmade and restrained.

#### Primary Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--cream` | `#F5F0E8` | Page background — the dominant surface color |
| `--cream-light` | `#FAF8F4` | Card backgrounds, elevated surfaces |
| `--cream-dark` | `#EDE7DB` | Hover states on cream, subtle borders |
| `--white` | `#FFFFFF` | High-contrast cards, input backgrounds, modals |
| `--black` | `#1A1A1A` | Primary text, strong headings |
| `--black-soft` | `#2D2D2D` | Secondary headings, active nav items |
| `--black-muted` | `#6B6B6B` | Body text, descriptions |
| `--black-faint` | `#9A9A9A` | Tertiary text, timestamps, metadata |

#### Functional Colors (used sparingly)

| Token | Value | Usage |
|-------|-------|-------|
| `--accent` | `#2C2C2C` | Primary buttons (dark on cream — high contrast) |
| `--accent-hover` | `#1A1A1A` | Button hover |
| `--success` | `#2D6A4F` | Completed states, certificates, pass badges |
| `--success-bg` | `#D8F3DC` | Success banner backgrounds |
| `--danger` | `#C1292E` | Delete actions, errors, failed states |
| `--danger-bg` | `#FDECEA` | Error banner backgrounds |
| `--warning` | `#B45309` | Caution states, pending reviews |
| `--warning-bg` | `#FEF3C7` | Warning banner backgrounds |
| `--info` | `#1E6091` | Informational badges, links |
| `--info-bg` | `#DBEAFE` | Info backgrounds |
| `--border` | `#E0DCD4` | Default borders on cream |
| `--border-strong` | `#C8C3B8` | Stronger dividers |
| `--border-on-white` | `#E5E5E5` | Borders on white cards |

#### Color Application Rules

1. **Page background is always cream** (`#F5F0E8`) — never pure white
2. **Cards and panels are white** (`#FFFFFF`) with a subtle `1px solid var(--border)` border
3. **Primary buttons are dark** (black on cream) — no colored buttons for primary actions
4. **Secondary/ghost buttons** have a `1px` border on cream background
5. **Danger buttons** are the only colored buttons — reserved for destructive actions
6. **Status badges** use muted functional colors with light backgrounds
7. **Links** are dark with underline — never bright blue
8. **No gradients**, no shadows deeper than `0 1px 3px rgba(0,0,0,0.06)`, no glows

### 3.2 Typography

**Font Stack:**
- **Headings**: `Space Grotesk` — geometric, modern, distinctive
- **Body/UI**: `Inter` — clean, highly readable at small sizes
- **Mono**: `IBM Plex Mono` — code blocks, certificate numbers, IDs

**Scale:**

| Name | Size | Weight | Font | Usage |
|------|------|--------|------|-------|
| Display | 32px | 500 | Space Grotesk | Page titles (Dashboard, My Courses) |
| Heading 1 | 24px | 500 | Space Grotesk | Section titles |
| Heading 2 | 20px | 500 | Space Grotesk | Card titles |
| Heading 3 | 16px | 600 | Inter | Subsection labels |
| Body Large | 16px | 400 | Inter | Lead paragraphs, descriptions |
| Body | 14px | 400 | Inter | Default text |
| Body Small | 13px | 400 | Inter | Metadata, timestamps |
| Caption | 12px | 500 | Inter | Labels, badges, hints |
| Mono | 13px | 400 | IBM Plex Mono | IDs, codes, technical values |

### 3.3 Spacing System

**Base unit**: 4px

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Icon/text micro-gaps |
| `--space-2` | 8px | Tight padding (badges, chips) |
| `--space-3` | 12px | Input padding, small gaps |
| `--space-4` | 16px | Card padding, form gaps |
| `--space-5` | 20px | Section gaps |
| `--space-6` | 24px | Major section padding |
| `--space-8` | 32px | Page-level padding |
| `--space-10` | 40px | Layout gutter |
| `--space-12` | 48px | Page margin (desktop) |
| `--space-16` | 64px | Major layout divisions |

### 3.4 Component Rules

#### Buttons

| Variant | Background | Text | Border | Usage |
|---------|-----------|------|--------|-------|
| Primary | `--black` | `--white` | none | Main actions (Save, Enroll, Publish) |
| Secondary | transparent | `--black` | `1px --border-strong` | Secondary actions (Cancel, Filter) |
| Ghost | transparent | `--black-muted` | none | Tertiary actions (Clear, Reset) |
| Danger | `--danger` | `--white` | none | Destructive only (Delete, Remove) |
| Small | same variants | same | same | In tables, compact contexts |

- Border radius: `6px`
- Height: `36px` (default), `32px` (small)
- Padding: `0 16px`
- Font: Inter 14px weight 500
- No uppercase. Sentence case always.

#### Cards

- Background: `--white` on cream pages
- Border: `1px solid var(--border)`
- Border radius: `8px`
- Padding: `20px`
- Shadow: `0 1px 2px rgba(0,0,0,0.04)` (barely visible)
- No hover effects unless clickable (then subtle border darken)

#### Forms

- Single-column layout, max-width `480px` for auth/profile
- Two-column for course editing (content + sidebar)
- Labels: Inter 13px weight 500, `--black-muted`, above input
- Inputs: white background, `1px solid var(--border)`, `6px` radius, `36px` height
- Error text: `--danger`, 13px, below input
- Spacing between fields: `16px`

#### Tables

- Minimal: no alternating row colors
- Thin `1px` bottom border between rows
- Header row: `--caption` font (12px, 500, uppercase), `--black-faint` text
- Row height: `48px`
- Hover: `--cream-dark` background
- Actions column: icon buttons or text links, right-aligned

#### Badges / Status Chips

| State | Background | Text |
|-------|-----------|------|
| Draft | `#F0EFEC` | `--black-muted` |
| Published / Ready | `--success-bg` | `--success` |
| Failed / Error | `--danger-bg` | `--danger` |
| Pending / Publishing | `--warning-bg` | `--warning` |
| Info / Active | `--info-bg` | `--info` |
| Completed | `--success-bg` | `--success` |
| Cancelled | `#F0EFEC` | `--black-faint` |

- Border radius: `4px`
- Padding: `2px 8px`
- Font: Inter 12px weight 500

---

## Part 4 — UI/UX Strategy

### 4.1 Making It Feel Non-AI and Professional

**Principles:**

1. **Asymmetric layouts** — Not everything is perfectly centered. Left-aligned content with right sidebar panels. This is how real product designers work.

2. **Visible editorial texture** — Use Space Grotesk's character in headings. Let the cream background breathe. Don't fill every pixel.

3. **Purposeful whitespace** — Give data room. A stat card doesn't need to touch the next stat card. Tables need padding.

4. **Human interaction copy** — "You're enrolled in JavaScript Foundations" not "Enrollment successful". "Add at least one module before publishing." not "Validation failed."

5. **No decorative elements** — No gradient hero. No abstract shapes. No floating particles. No emoji in headings. Just content.

6. **Real content density** — Show actual data, not placeholder illustrations. Tables over big cards when there are >5 items.

7. **Consistent empty states** — Every empty state explains what to do next. "You haven't enrolled in any courses yet. Browse the catalog to get started."

8. **Subtle, honest loading** — Skeleton screens that match the actual content shape. Never a full-page spinner.

### 4.2 Dashboard Layout Strategy

**Student Dashboard:**
```
┌─────────────────────────────────────────────────────┐
│  Welcome back, Jane.                                │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Active: 3│ │ Done: 5  │ │ Certs: 5 │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│                                                     │
│  Continue Learning                                  │
│  ┌─────────────────────────────────────────────┐    │
│  │ JavaScript Foundations  ████████░░░  80%     │    │
│  │ Last activity: 2 hours ago     [Continue →] │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │ Data Science 101       ███░░░░░░░░  30%     │    │
│  │ Last activity: yesterday       [Continue →] │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  Recent Certificates                                │
│  ┌────────────────────────────┐                     │
│  │ SC-2026-00042 · ML Basics  │ [View]              │
│  └────────────────────────────┘                     │
└─────────────────────────────────────────────────────┘
```

**Instructor Workspace:**
```
┌───────────────────────────────────────────────────────┐
│  My Courses                          [+ Create New]   │
│                                                       │
│  Drafts (2)                                           │
│  ┌─────────────────────────────────────────────┐      │
│  │ Advanced Python        DRAFT    [Edit →]    │      │
│  │ 3 modules · 5 assets · Not validated        │      │
│  └─────────────────────────────────────────────┘      │
│                                                       │
│  Published (3)                                        │
│  ┌─────────────────────────────────────────────┐      │
│  │ JavaScript Foundations  READY    [Manage →]  │      │
│  │ v2 · 142 enrollments · 95% completion       │      │
│  └─────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────┘
```

**Admin Dashboard:**
```
┌──────────────────────────────────────────────────────┐
│  Platform Overview              [Apr 1 – Apr 20 ▾]  │
│                                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │  247 │ │  89  │ │  34  │ │ 1.2K │ │  12  │      │
│  │Users │ │Enroll│ │Compl.│ │AI Qry│ │Cours.│      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
│                                                      │
│  Recent Activity                    [View all →]     │
│  ┌─────────────────────────────────────────────┐     │
│  │ User  │ Action        │ Resource  │ Time    │     │
│  │ admin │ ROLE_CHANGED  │ user-42   │ 2m ago  │     │
│  │ jane  │ ENROLLED      │ course-7  │ 15m ago │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  Pending Reviews (3)                                 │
│  ┌─────────────────────────────────────────────┐     │
│  │ John Doe · Professor at MIT · 3 days ago    │     │
│  │ "I want to publish my NLP course..."        │     │
│  │                     [Approve] [Reject]      │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### 4.3 Handling Dense Data

| Data Type | Pattern | Why |
|-----------|---------|-----|
| User list (admin) | Dense table with inline actions | Admins need to scan fast. Cards waste space. |
| Course list (instructor) | Stacked list items with metadata line | Instructors manage 5-20 courses, need status at a glance |
| Enrollment list (student) | Cards with progress bars | Students need visual progress, emotional feedback |
| Module list (curriculum) | Vertical stack with drag handles | Reordering is the primary interaction |
| Asset list | Table rows grouped by module | Files are data; cards are overkill |
| Notifications | Simple list with unread indicator | Speed of scanning > decoration |
| Audit log | Dense table with filters | Operational; needs maximal information density |
| AI Q&A | Chat-style thread | Conversational interaction requires sequential layout |
| AI enhancement jobs | Status cards with timeline | Jobs have lifecycle; status is the primary information |
| Publishing steps | Vertical timeline | Sequential process needs sequential UI |
| Certificates | Cards with share action | Certificates are achievements; deserve visual weight |
| MCQ quizzes (AI-generated) | Numbered list with radio options | Standard quiz UI; don't reinvent |
| Analytics KPIs | Stat cards in a horizontal row | Quick scan of key numbers |

---

## Part 5 — Role-Wise Breakdown

### 5.1 Student Interface

#### Pages

| Page | Route | Key Features |
|------|-------|-------------|
| **Dashboard** | `/app/dashboard` | Welcome greeting, stat summary (active/completed/certs), continue learning cards sorted by last activity, recent notifications preview |
| **Learning** | `/app/learning` | All enrollments with status filter (Active/Completed/Cancelled), progress bars, sort by last activity or title |
| **Learning Workspace** | `/app/learning/:enrollmentId` | Module checklist with completion toggles, course info sidebar, progress ring, AI assistant panel (slide-out or inline), certificate display on completion |
| **Certificates** | `/app/certificates` | Grid of certificate cards with course title, issue date, certificate number, share link |
| **Certificate Detail** | `/certificates/:certificateId` | Printable/shareable certificate view, verification badge, public access |
| **Catalog** | `/catalog` or `/app/catalog` | Filter bar (category, difficulty, tags), course cards grid, sort by relevance/date, responsive columns |
| **Course Detail** | `/catalog/:courseId` | Hero section, enrollment decision card (context-aware CTA), learning outcomes, module preview, AI availability note |
| **Search** | `/search` or `/app/search` | Search-first layout, large query input, real-time results, filter refinement |
| **Notifications** | `/app/notifications` | Chronological list, unread filter, mark-read actions, link to relevant resource |
| **Profile** | `/app/profile` | Name/avatar edit form, role display, instructor application form (if student only) |
| **Settings** | `/app/settings` | Notification preferences (email toggles per event type) |

#### Layout Strategy
- **Sidebar nav**: Dashboard, My Learning, Certificates, Catalog, divider, Notifications, Profile
- **Dashboard is the landing page** — optimized for resuming, not browsing
- **Learning workspace** uses a left panel (module list) + right content area
- **AI assistant** appears as a collapsible right panel inside the learning workspace

#### Key Student Flows
1. **Discover → Evaluate → Enroll**: Catalog → Course Detail → Enroll CTA → Redirect to Learning Workspace
2. **Resume → Complete**: Dashboard → Continue Learning card → Module Checklist → Mark Complete → Certificate
3. **Ask AI**: Inside Learning Workspace → Open assistant panel → Ask question → See cited answer

---

### 5.2 Instructor Interface

#### Pages

| Page | Route | Key Features |
|------|-------|-------------|
| **Courses Workspace** | `/app/courses` | Create new CTA, course list grouped by status (Drafts/Published/Archived), search/filter, quick-access to last edited |
| **Create Course** | `/app/courses/new` | Focused form: title, description, category, difficulty, duration, tags. Redirect to overview on create. |
| **Course Overview** | `/app/courses/:courseId/overview` | Course details form, status chip, version summary, validation summary sidebar, last updated timestamp |
| **Curriculum** | `/app/courses/:courseId/curriculum` | Module list with add/edit/delete/reorder, required toggle, asset count per module, inline editing |
| **Assets** | `/app/courses/:courseId/assets` | Upload zone, assets grouped by module, type badges, download/delete actions, upload status indicators |
| **AI Tools** | `/app/courses/:courseId/ai` | Enhancement job launcher (summary/quiz/glossary/objectives), scope selector (course/module), active jobs list, completed results display, streaming preview |
| **Publish** | `/app/courses/:courseId/publish` | Validation results, publish button (disabled if invalid), active publishing timeline, version history table, retry/cancel actions |
| **Course Analytics** | `/app/courses/:courseId/analytics` | Enrollment count, completion rate, AI query count, module-level completion breakdown |

#### Layout Strategy
- **Sidebar nav**: My Courses, (if also student: Dashboard, Learning, Certificates), Catalog, divider, Notifications, Profile
- **Course editor uses a tab navigation** under the course name: Overview | Curriculum | Assets | AI | Publish | Analytics
- **Tab nav persists the course context** — never lose orientation about which course you're editing
- **Create flow is a separate clean page** — not a modal on the workspace

#### Key Instructor Flows
1. **Create → Structure → Upload → Publish**: Create Course → Curriculum (add modules) → Assets (upload files) → Publish (validate → publish)
2. **Monitor Publish**: Publish tab → Watch timeline → See READY status → Version appears in history
3. **Enhance with AI**: AI tab → Select job type → Choose scope → Launch → Watch streaming result
4. **Review Performance**: Analytics tab → See enrollment/completion/AI metrics

---

### 5.3 Admin Dashboard

#### Pages

| Page | Route | Key Features |
|------|-------|-------------|
| **Users** | `/app/admin/users` | Dense table with search, role filter, status filter, inline role toggle, activate/deactivate, link to audit context |
| **Applications** | `/app/admin/instructor-applications` | Status tabs (Pending/Approved/Rejected), application cards with applicant name, reason, date, approve/reject actions with confirmation |
| **Platform Analytics** | `/app/admin/analytics` | Date range picker, KPI stat row (students, enrollments, completions, AI usage, published courses), activity trends (when available) |
| **Workflows** | `/app/admin/workflows` | Table with status filter, course filter, workflow list showing course, status, initiated by, timestamps, retry action |
| **Workflow Detail** | `/app/admin/workflows/:id` | Step timeline (validate → extract → chunk → embed → index → finalize), error details, artifacts, retry/cancel buttons |
| **Audit Log** | `/app/admin/audit-log` | Dense table with filters (actor, action, resource type, date range), sortable, correlation IDs visible |
| **DLQ** | `/app/admin/dlq` | Message list with topic, error, timestamp, payload preview, replay button with confirmation |

#### Layout Strategy
- **Admin uses a dedicated sub-nav within the sidebar** — separated from product navigation
- **Sidebar**: Admin label → Users, Applications, Analytics, Workflows, Audit Log, DLQ; divider; (product links if multi-role)
- **Tables are the primary pattern** — admins need density, not decoration
- **Every destructive action requires confirmation dialog**
- **Correlation IDs are clickable** → link to audit log filtered by that ID

#### Key Admin Flows
1. **Review Application**: Applications → See pending → Read reason → Approve → Confirmation → Status updates
2. **Investigate Issue**: Audit Log → Filter by user → See action history → Follow correlation ID to workflow
3. **Fix Failed Publish**: Workflows → Filter by FAILED → Open detail → Read error → Retry → Monitor timeline
4. **Platform Health Check**: Analytics → Review KPIs → Check recent audit activity

---

## Part 6 — Execution Plan

### 6.1 Build Priority Order

**Sprint 1 — Foundation (Days 1-2)**
1. Set up design tokens CSS (`tokens.css`, `reset.css`, `utilities.css`)
2. Build primitive UI components: Button, Input, Badge, Card, Modal, ConfirmDialog, Skeleton, EmptyState, ErrorState
3. Build layout shells: PublicLayout, AuthLayout, AppShell (with Sidebar + TopBar)
4. Wire up new router structure with layouts
5. Migrate session/auth logic (no changes needed — just import restructuring)

**Sprint 2 — Auth + Shared Components (Days 3-4)**
6. Build form components: FormField, FormStack, SearchInput
7. Build data components: DataTable, FilterBar, Pagination, StatCard, StatRow, ProgressBar
8. Build navigation: Sidebar, TopBar, Breadcrumbs, TabNav, NotificationBell
9. Rebuild auth pages (Login, Register, Verify, Forgot, Reset) using new components
10. Rebuild ProfilePage and SettingsPage

**Sprint 3 — Student Interface (Days 5-7)**
11. Build student components: ContinueLearningCard, EnrollmentCard, ModuleChecklist, ProgressRing, CertificateCard
12. Build DashboardPage
13. Build LearningPage + LearningWorkspacePage
14. Build CertificatesPage + CertificateDetailPage
15. Build CatalogPage + SearchPage + CourseDetailPage (with enrollment flow)

**Sprint 4 — Instructor Interface (Days 8-10)**
16. Build instructor components: CourseListItem, ModuleEditor, AssetUploader, ValidationPanel, PublishTimeline, VersionHistory
17. Build CoursesWorkspacePage + CreateCoursePage
18. Build CourseOverviewPage + CurriculumPage + AssetsPage
19. Build PublishPage with timeline
20. Build AIToolsPage + CourseAnalyticsPage
21. Build CourseTabNav and wire sub-routing

**Sprint 5 — Admin Interface (Days 11-12)**
22. Build admin components: UserRow, RoleManager, ApplicationReviewCard, WorkflowStepTimeline
23. Build UsersPage + ApplicationsPage
24. Build PlatformAnalyticsPage
25. Build WorkflowsPage + WorkflowDetailPage
26. Build AuditLogPage + DLQPage

**Sprint 6 — AI + Notifications + Polish (Days 13-14)**
27. Rebuild AI Assistant panel with citation cards
28. Rebuild AI Enhancement panel with job management
29. Build NotificationsPage with real API integration
30. Notification bell with unread count (polling)
31. Responsive breakpoints pass (tablet + mobile)
32. Empty state, loading state, error state consistency pass

### 6.2 Reusable Components Strategy

**High reuse (build first):**
- `Button` — used on every page
- `Card` — used in dashboards, lists, detail views
- `DataTable` — used in admin, asset lists, enrollment lists
- `Badge` / `StatusChip` — used everywhere status appears
- `FormField` + `FormStack` — every form
- `EmptyState` — every list
- `Skeleton` — every async page
- `Pagination` — every list endpoint
- `StatCard` / `StatRow` — dashboards and analytics
- `FilterBar` — catalog, admin tables, audit log

**Medium reuse (build in feature sprint):**
- `ProgressBar` / `ProgressRing` — student pages
- `Timeline` — publishing, workflow detail
- `TabNav` — course editor, admin sections
- `ConfirmDialog` — destructive actions across all roles
- `NotificationBell` — app shell (shared)

**Feature-specific (build inline):**
- `ModuleChecklist` — learning workspace only
- `AssetUploader` — course editor only
- `AIAssistantPanel` — learning workspace + AI tools
- `CourseHero` — course detail page only
- `RoleManager` — admin users page only

### 6.3 What NOT to Change

- `lib/api.ts` — Complete. Don't touch. Only extend if a new endpoint is needed.
- `lib/session.ts` — Working session management. Keep as-is.
- `lib/types.ts` — Response types are correct. Add new types in feature files if needed.
- Backend services — Zero changes. Frontend consumes existing API contracts exactly.
- Docker/infrastructure — No changes.

---

## Part 7 — Risk Handling

### 7.1 Avoiding Backend Breakage

| Risk | Mitigation |
|------|-----------|
| Changing API call signatures | Don't modify `lib/api.ts`. Import existing functions. |
| Wrong endpoint paths | All paths already defined as constants in api.ts (`AUTH_BASE`, `COURSE_BASE`, etc.) |
| Missing auth headers | `requestEnvelope()` already adds Bearer token from session |
| Token expiry during use | api.ts already handles 401 → refresh → retry |
| Wrong request body shapes | All input types already defined and validated by Zod |

### 7.2 API Validation Approach

1. **Keep all existing API call functions unchanged** — they are tested and working
2. **Use browser Network tab** during development to verify request/response shapes match docs
3. **Use React Query devtools** to inspect cached data and verify types
4. **Test each flow end-to-end against the running backend** before marking feature complete
5. **Use correlation IDs from error responses** to trace issues to backend logs

### 7.3 What Could Go Wrong

| Issue | Resolution |
|-------|-----------|
| Notification API not returning expected shape | The API contracts doc specifies the shape. If real response differs, adjust frontend types only. |
| Course analytics endpoint returns empty | Backend analytics consumer may need events first. Test after performing actions. |
| SSE streaming breaks on rebuild | `requestEventStream()` already handles SSE parsing. Keep the same function. |
| Route guards too aggressive | Test with all three role types (student, instructor, admin) after building router. |
| CSS specificity conflicts | Use BEM-style naming or CSS modules. Don't rely on global class inheritance. |

---

## Summary

| Aspect | Decision |
|--------|----------|
| **Theme** | Cream page backgrounds, white cards, black text, no color accents except functional (success/danger/warning) |
| **Fonts** | Space Grotesk (headings), Inter (body), IBM Plex Mono (code) |
| **Components** | ~30 shared primitives built before features |
| **Architecture** | Feature-folder per role, shared components, existing API layer untouched |
| **Routing** | 3 layouts (public, auth, app), role-guarded sections, instructor course sub-tabs |
| **Data patterns** | Tables for admin, cards for students, tab panels for instructor workspace |
| **AI** | Slide-out panel in learning workspace, dedicated page in instructor workspace |
| **Mobile** | Responsive with sidebar → hamburger collapse |
| **Sprints** | 6 sprints (~14 days) from foundation to polish |
| **Backend** | Zero changes. All 70+ API functions reused as-is. |
