# EduCorp — Frontend Architecture

## Overview

EduCorp ships a first-party web application from `apps/web`. The frontend is built in parallel with the backend phases so each phase can be exercised by real user flows, not just API calls.

Phase 1 covers authentication, account recovery, profile management, and a thin admin console for user and instructor-application operations.

Phase 2 adds the first real product workflow for instructors and admins: course draft creation, metadata editing, module management, MinIO-backed asset operations, draft validation, and Mongo-backed rich draft content.

## Product Boundaries

- The web app consumes the public REST API through Traefik under `/api/v1/*`.
- There is no separate backend-for-frontend in Phase 1 or Phase 2.
- Access tokens stay short-lived and refresh tokens are rotated through the existing auth endpoints.
- Server-side authorization remains the source of truth. Client guards improve UX but do not replace backend checks.

## Stack

- React 19 + TypeScript
- Vite for local development and production builds
- React Router for route composition
- TanStack Query for API state and cache invalidation
- React Hook Form + Zod for auth and admin forms
- Vitest + Testing Library for frontend tests

## Directory Shape

```text
apps/web/
├── public/
├── src/
│   ├── app/            # Router, providers, bootstrapping
│   ├── features/
│   │   ├── auth/       # Register, login, verify, reset, session logic
│   │   ├── catalog/    # Phase 3 placeholder pages (catalog browse, search)
│   │   ├── courses/    # Draft course workspace, modules, assets, validation, draft content
│   │   ├── profile/    # Current user profile screens
│   │   └── admin/      # Users and instructor applications
│   ├── lib/            # HTTP client, env config, query helpers
│   └── index.css       # Tokens, resets, and all component CSS
├── package.json
└── vite.config.ts
```

## Route Plan

### Public routes

- `/login`
- `/register`
- `/verify-email`
- `/forgot-password`
- `/reset-password`

### Protected routes

- `/app/courses` — Course authoring workspace (instructor/admin)
- `/app/courses/:courseId` — Course editor (instructor/admin)
- `/app/catalog` — Course catalog browse (Phase 3 placeholder)
- `/app/search` — Search courses (Phase 3 placeholder)
- `/app/profile` — Current user profile
- `/app/admin/users` — Admin user management
- `/app/admin/instructor-applications` — Admin application review

## State and Session Model

- Persist the refresh token locally for development convenience in Phase 1.
- Keep the access token in memory and refresh it centrally on `401` responses when refresh is available.
- Store the decoded user summary and roles in app state after login and refresh.
- Default instructors and admins into the authoring workspace; students land on profile.
- On refresh failure, clear session state and return to `/login`.

## Design System

The frontend uses a professional, restrained SaaS aesthetic: white content surfaces against a warm light background, tight radii, and functional typography. The system is defined entirely in CSS custom properties in `index.css`.

### Design Principles

- Clean and flat over decorative gradients and glows
- Task-completion focus over marketing-site composition
- Dense, readable tables and filter bars over oversized cards
- Explicit, human-readable error states from the API response envelope
- Single-column forms with optional side panels for validation and metadata

### Color Tokens

- `--color-bg: #f7f6f3` — page background (warm off-white)
- `--color-surface: #ffffff` — card / panel surfaces (clean white)
- `--color-surface-alt: #f0efec` — alternate backgrounds
- `--color-surface-hover: #eae9e5` — hover state
- `--color-text: #1a1a1a` — primary text
- `--color-text-secondary: #5a5a57` — muted text
- `--color-text-tertiary: #8a8a87` — tertiary / hint text
- `--color-border: #e2e1dd` — default borders
- `--color-border-strong: #cccbc6` — stronger borders
- `--color-accent: #e04e00` — primary action color (burnt orange)
- `--color-danger: #c4232a` — destructive actions
- `--color-success: #177a56` — positive feedback
- `--color-warning: #b45309` — caution

### Typography

- Display/UI sans: `Space Grotesk`, fallback `system-ui`
- Editorial/body serif: `Newsreader`, fallback `Georgia`
- Mono: `IBM Plex Mono`, fallback `ui-monospace`

### Radius and Depth

- `--radius-sm: 4px` — buttons, inputs, badges
- `--radius-md: 6px` — cards, panels
- `--radius-lg: 8px` — modals, larger containers
- Shadows are minimal: `--shadow-xs` through `--shadow-lg`, used sparingly

### Component Classes

| Category | Classes |
|----------|---------|
| Layout | `.app-shell`, `.app-header`, `.app-main`, `.page-stack`, `.page-columns`, `.page-header` |
| Buttons | `.btn`, `.btn--primary`, `.btn--ghost`, `.btn--danger`, `.btn--sm`, `.btn-row` |
| Cards | `.card`, `.card__header`, `.card__title`, `.card__description` |
| Forms | `.form-stack`, `.form-row`, `.form-field`, `.form-field__label` |
| Tables | `.table-wrap`, `.table`, `.filter-bar` |
| Badges | `.badge`, `.badge--accent`, `.badge--success`, `.badge--danger`, `.badge--warning` |
| Messages | `.message`, `.message--success`, `.message--error`, `.message--warning` |
| Empty | `.empty` |
| Auth | `.auth-page`, `.auth-card`, `.auth-hint` |
| Stats | `.stat-row`, `.stat-item` |
| Meta | `.meta-list`, `.meta-item` |
| Courses | `.course-list`, `.course-item`, `.module-panel`, `.asset-row` |
| Validation | `.validation-result`, `.validation-issue` |
| Placeholder | `.placeholder-page` (Phase 3+ stub pages) |

## Screen Rules

- Authentication pages use a single centered card layout (`.auth-page > .auth-card`).
- Form layouts favor a single clear column. The course editor uses a two-column layout for details + validation.
- Admin screens use dense, readable tables and flat filter bars.
- Authoring screens (course editor) show stats at the top, course details and validation side-by-side, and modules below.
- The course workspace exposes real API feedback, not fake completion states.
- Error states use the API response envelope's `error.message` via `.message--error`.

## Testing Expectations

- Cover core auth forms, route guards, and API session behavior with Vitest.
- Prefer integration-style component tests over snapshot-heavy tests.
- Keep a small number of tests focused on user-critical flows: register, login, refresh/logout failure, profile update, admin access restrictions, and authoring route/API behavior.