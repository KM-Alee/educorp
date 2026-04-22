# Frontend/Backend Gap Audit

## Summary

This audit compared `/home/kali/proj/educorp/apps/web` against `/home/kali/proj/educorp/services/*`, `/home/kali/proj/educorp/docs/API_CONTRACTS.md`, and `/home/kali/proj/educorp/docs/PHASES.md`.

Highest-impact user-visible gaps:

1. Public catalog/search works only halfway; public course detail is effectively broken.
2. Notifications and notification settings are exposed in navigation but still mock/placeholder UX.
3. Admin enrollment pages present a workflow and statuses the backend does not support.
4. AI instructor tools are shown to instructors who are not course owners, causing avoidable 403s.
5. Backend enrollment/capacity/prerequisite features are only partially reachable because authoring UI omits key course fields.
6. Several frontend assumptions match current backend code but not the published API contracts.

## Confirmed frontend/backend gaps

### 1) Public catalog/search routes lead into a protected course-detail flow

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/catalog/CatalogPages.tsx` links results to `/app/catalog/:courseId`.
- `/home/kali/proj/educorp/apps/web/src/app/router.tsx` has public `/catalog` and `/search`, but course detail exists only at protected `/app/catalog/:courseId`.
- `/home/kali/proj/educorp/apps/web/src/lib/api.ts` calls `getCourse`, `listModules`, `listAssets`, and `getAssetDownload` with authenticated requests.

**Backend/docs evidence**
- `/home/kali/proj/educorp/services/course/app/api/v1/courses.py` exposes `GET /courses/{course_id}` with optional auth and returns course details.
- `docs/API_CONTRACTS.md` describes public catalog browsing and `GET /courses/{course_id}` returning module summaries.

**Impact**
- Logged-out users can browse search results but cannot open a course detail page without being redirected to login.
- The frontend suggests a public catalog, but the detailed learning/purchase decision page is not actually public.

### 2) Public course detail is over-coupled to auth-only module/material endpoints

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/courses/StudentCoursePage.tsx` fetches:
  - `getCourse(courseId)`
  - `listModules(courseId)`
  - `listAssets(courseId, moduleId)`
- It does not rely on the `modules` already present in `getCourse()` responses.

**Backend evidence**
- `/home/kali/proj/educorp/services/course/app/api/v1/modules.py` requires an authenticated current user for `GET /{course_id}/modules`.
- `/home/kali/proj/educorp/services/course/app/api/v1/assets.py` requires an authenticated current user for asset listing/download.

**Impact**
- Even if the route were made public, the current frontend data flow would still fail for anonymous visitors.
- The backend does return modules on `GET /courses/{id}`, but the frontend ignores that and makes stricter follow-up calls.

### 3) Notifications page is still a placeholder even though notification APIs are implemented

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/notifications/NotificationsPage.tsx` is pure placeholder text; no API calls.
- `/home/kali/proj/educorp/apps/web/src/app/router.tsx` and app shell expose `/app/notifications`.

**Backend evidence**
- `/home/kali/proj/educorp/services/notification/app/api/v1/notifications.py` implements:
  - `GET /notifications`
  - `PATCH /notifications/{id}/read`
  - `POST /notifications/read-all`
  - `GET/PATCH /notifications/preferences`

**Impact**
- Users are routed to a non-functional page for a feature that already has backend support.
- This is misleading because the navigation implies a working inbox.

### 4) Settings page is static and does not persist real notification preferences

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/settings/SettingsPage.tsx` renders local checkboxes only and explicitly says preferences are “not persisted yet”.

**Backend evidence**
- `/home/kali/proj/educorp/services/notification/app/api/v1/notifications.py` already supports getting/updating preferences.

**Impact**
- Users can change settings visually but nothing is saved.
- The screen is especially misleading because it is presented as a real account settings page, not a prototype.

### 5) Admin enrollment UI assumes nonexistent statuses and a nonexistent approval workflow

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/admin/AdminPages.tsx`
  - Dashboard asks for `listAllEnrollments({ status: 'PENDING' })`
  - Labels the page “Enrollment approvals”
  - Badge logic expects `PENDING` and `ACTIVE`
- It treats enrollments as something admins approve/reject.

**Backend evidence**
- `/home/kali/proj/educorp/services/enrollment/app/models/enrollment.py` and service code use only:
  - `ENROLLED`
  - `COMPLETED`
  - `CANCELLED`
- No `PENDING`
- No `ACTIVE`
- No admin approval flow for enrollments

**Impact**
- “Pending enrollments” cards will always be empty.
- Status badges are wrong/misleading.
- The UI describes a workflow the system does not implement.

### 6) Instructor enrollment roster endpoint lacks ownership enforcement

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/courses/CoursePages.tsx` exposes `/app/courses/:courseId/enrollments` for any instructor/admin via role guard only.

**Backend evidence**
- `/home/kali/proj/educorp/services/enrollment/app/api/v1/enrollments.py` exposes `GET /courses/{course_id}/enrollments` for `instructor` or `admin`.
- That handler calls repository listing directly and does not verify that the instructor owns the course.

**Impact**
- Any instructor who knows or guesses another course ID can inspect another instructor’s enrollments.
- This is a real server-side permission gap, not just a frontend issue.

### 7) AI enhancement tools are shown to non-owner instructors and will 403

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/courses/StudentCoursePage.tsx` shows `AIEnhancementPanel` for any user with `instructor` or `admin` role.
- It does not check course ownership.

**Backend evidence**
- `/home/kali/proj/educorp/services/ai/app/api/v1/instructor.py` requires instructor/admin role.
- `/home/kali/proj/educorp/services/ai/app/repositories/entitlement_repository.py` and `_require_owner()` enforce course ownership for instructors.

**Impact**
- Non-owner instructors get a UI that invites them to run jobs, then receive 403 errors.
- This is a concrete frontend/backend permission mismatch.

### 8) Course authoring UI does not expose backend fields needed for enrollment behavior

**Frontend evidence**
- `/home/kali/proj/educorp/apps/web/src/features/courses/CoursePages.tsx` course forms expose title, description, category, difficulty, duration, tags.
- The editor does not expose:
  - `max_capacity`
  - `prerequisites`
  - `thumbnail_url`
  - `is_public_preview`

**Backend evidence**
- `/home/kali/proj/educorp/services/course/app/schemas/course.py` supports those fields in create/update.
- `docs/API_CONTRACTS.md` includes `max_capacity` and `prerequisites`.

**Impact**
- Instructors cannot configure capacity limits or prerequisites from the first-party UI.
- That blocks meaningful Phase 4 enrollment scenarios from being set up through the frontend.
- Preview/presentation features are also not manageable.

## Likely contract mismatches

### 1) Admin API base path differs between docs and implementation
- `docs/API_CONTRACTS.md` documents admin endpoints under `/api/v1/admin/...`.
- Actual backend routes are under `/api/v1/auth/admin/...` because admin routes are mounted inside auth service.
- Frontend `/home/kali/proj/educorp/apps/web/src/lib/api.ts` matches the implementation, not the docs.

**Risk**
- Third-party or future frontend consumers built from the docs will call the wrong URLs.

### 2) Analytics response shape differs from docs
- `docs/API_CONTRACTS.md` describes rich nested analytics (`period`, timeseries, detailed `ai_usage`, etc.).
- Actual backend schema in `/home/kali/proj/educorp/services/analytics/app/schemas/analytics.py` is flat:
  - `from_date`
  - `to_date`
  - `total_students`
  - `enrollments`
  - `completions`
  - `ai_usage`
  - `published_courses`
- Frontend `/home/kali/proj/educorp/apps/web/src/lib/api.ts` matches the flat backend.

**Risk**
- Docs over-promise analytics richness the current backend and UI do not provide.

### 3) Search “browse” contract differs from docs
- `docs/API_CONTRACTS.md` says `/search/courses` requires `q`.
- Backend `/home/kali/proj/educorp/services/search/app/api/v1/search.py` makes `q` optional.
- Frontend `CatalogPage` uses `/search/courses` without `q` as a browse endpoint.

**Risk**
- Contract drift: current frontend behavior depends on undocumented backend behavior.

## Frontend flows blocked by missing backend behavior

### 1) True anonymous catalog detail is not fully supported as a coherent contract
The product shape suggests:
- public browse
- public course detail
- then enrollment/login when needed

But the effective API contract is fragmented:
- `GET /courses/{id}` is public-capable
- `GET /courses/{id}/modules` requires auth
- asset listing/download also require auth

Because the frontend uses the stricter endpoints, the anonymous flow breaks. Even after fixing routing, either:
- the frontend must rely only on `GET /courses/{id}` for public detail, or
- the backend needs a documented public published-course/modules/materials contract.


### 3) Enrollment “approval” flow shown in admin UI has no backend equivalent
The UI implies a moderation queue, but backend enrollment creation is direct/idempotent.

**Frontend consequence**
- The workflow cannot ever work as shown.
- This should be removed or redesigned, not just “wired up”.

## Backend features missing UI coverage

### 1) Notification inbox features
Backend exists for:
- list notifications
- mark read
- mark all read
- get/update preferences

But UI coverage is missing or placeholder in:
- `/home/kali/proj/educorp/apps/web/src/features/notifications/NotificationsPage.tsx`
- `/home/kali/proj/educorp/apps/web/src/features/settings/SettingsPage.tsx`

### 2) Course analytics endpoint
Backend exists:
- `/home/kali/proj/educorp/services/analytics/app/api/v1/analytics.py` → `GET /analytics/courses/{course_id}`

UI coverage is missing:
- no instructor course analytics screen
- no course analytics section in the course workspace/editor

### 3) Course metadata fields needed for enrollment controls
Backend supports:
- `max_capacity`
- `prerequisites`
- `thumbnail_url`
- `is_public_preview`

UI coverage is missing in:
- `/home/kali/proj/educorp/apps/web/src/features/courses/CoursePages.tsx`

### 4) Notification preference granularity
Backend supports more detailed notification preference controls than the current Settings page exposes.

### 5) Some publishing operations are only partially surfaced
Backend supports:
- approve
- reject
- cancel
- activate
- retry

UI coverage exists mainly inside the course editor pipeline view, but not as a full admin operations surface tied to workflow lists. The admin workflows page supports inspect/retry only.

## Recommended sequencing

### 1) Fix the public catalog detail flow first
- Add a real public course detail route or change public result links.
- Stop requiring auth-only helper calls for anonymous detail pages.
- Prefer `GET /courses/{id}` data for public detail; only fetch extra protected data after login/enrollment.

### 2) Remove or hide misleading placeholder pages until they are wired
- Either implement Notifications and Settings against the existing notification APIs, or remove them from nav.
- Do the same for any “approval” language around enrollments.

### 3) Align enrollment UI with real backend states
- Remove `PENDING` and `ACTIVE` assumptions from admin pages.
- Rename “Enrollment approvals” to an actual admin enrollment overview.
- Add ownership enforcement to instructor course-enrollment listing on the backend.


### 5) Expose missing course configuration fields in authoring
- Add `max_capacity`, `prerequisites`, preview/publicity controls, and thumbnail fields to course create/edit screens.
- Without this, core Phase 4 behaviors remain difficult or impossible to exercise from the frontend.

