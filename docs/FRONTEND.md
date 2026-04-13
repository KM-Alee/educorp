# EduCorp — Frontend Architecture

## Overview

EduCorp ships a first-party web application from `apps/web`. The frontend is built in parallel with the backend phases so each phase can be exercised by real user flows, not just API calls.

Phase 1 covers authentication, account recovery, profile management, and a thin admin console for user and instructor-application operations.

## Product Boundaries

- The web app consumes the public REST API through Traefik under `/api/v1/*`.
- There is no separate backend-for-frontend in Phase 1.
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
│   ├── components/     # Shared shell and presentational pieces
│   ├── features/
│   │   ├── auth/       # Register, login, verify, reset, session logic
│   │   ├── profile/    # Current user profile screens
│   │   └── admin/      # Users and instructor applications
│   ├── lib/            # HTTP client, env config, query helpers
│   └── styles/         # Tokens and global CSS
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

- `/app/profile`
- `/app/admin/users`
- `/app/admin/instructor-applications`

## State and Session Model

- Persist the refresh token locally for development convenience in Phase 1.
- Keep the access token in memory and refresh it centrally on `401` responses when refresh is available.
- Store the decoded user summary and roles in app state after login and refresh.
- On refresh failure, clear session state and return to `/login`.

## Design System Adaptation

The frontend takes the warm editorial tone from `cursor-inspo.md` and adapts it for an operational product UI.

### Keep

- Warm cream background family anchored by `#f2f1ed`
- Dark warm-brown primary text anchored by `#26251e`
- Expressive headline typography with tighter tracking
- Soft warm borders, compact radii, and pill filters where useful
- Sparse, meaningful motion and restrained depth

### Adapt

- Use open, shippable fonts instead of Cursor's proprietary typefaces
- Apply the visual language to forms, tables, panels, and navigation rather than to hero sections
- Use editor-inspired mono accents only for technical labels, tokens, or status metadata
- Keep shadows subtle and mostly reserve heavier elevation for modal or command surfaces

### Avoid

- Large decorative gradients
- Glow effects and glassmorphism
- Generic AI motifs, animated sparkles, or chatbot styling on core auth screens
- Marketing-site composition patterns that get in the way of task completion

## Recommended Tokens

### Color

- `--color-bg: #f2f1ed`
- `--color-surface: #e6e5e0`
- `--color-surface-soft: #ebeae5`
- `--color-text: #26251e`
- `--color-text-muted: rgba(38, 37, 30, 0.66)`
- `--color-border: rgba(38, 37, 30, 0.12)`
- `--color-border-strong: rgba(38, 37, 30, 0.24)`
- `--color-accent: #f54e00`
- `--color-danger: #cf2d56`
- `--color-success: #1f8a65`

### Typography

- Display/UI sans: `Space Grotesk`, fallback `system-ui`
- Editorial/body serif: `Newsreader`, fallback `Georgia`
- Mono: `IBM Plex Mono`, fallback `ui-monospace`

### Radius and depth

- Cards and primary controls: `8px`
- Compact controls: `4px`
- Pills: `9999px`
- Default shadow: minimal or none
- Elevated shadow: diffuse and warm, used sparingly

## Phase 1 Screen Rules

- Authentication pages should feel calm and trustworthy, not like a launch page.
- Form layouts should favor a single clear column with one secondary support panel at most.
- Admin screens should use dense but readable tables and filter bars with warm borders and low visual noise.
- Error states should be explicit and human-readable using the API response envelope's `error.message`.

## Testing Expectations

- Cover core auth forms, route guards, and API session behavior with Vitest.
- Prefer integration-style component tests over snapshot-heavy tests.
- Keep a small number of tests focused on user-critical flows: register, login, refresh/logout failure, profile update, and admin access restrictions.