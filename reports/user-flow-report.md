# User Flow Report

## Executive summary

EduCorp already implements most of the core product surface promised in the docs: auth, authoring, publishing, catalog/search, enrollment, progress, certificates, AI, notifications, analytics, and admin operations all exist in code. The strongest end-to-end stories today are the auth flow, the instructor draft-to-publish flow, and the student enroll-to-complete flow.

The main product problem is not missing breadth. It is flow coherence. Several journeys disagree across frontend, backend, and docs. A few are actively broken in user terms: anonymous catalog browsing dead-ends at login, enrolled learners cannot actually download materials, notifications are implemented server-side but still shown as placeholders, and instructors lose a clear home for courses once those courses go live. There are also multiple places where the UI implies product rules that the backend does not support, especially around admin enrollment review, instructor ownership boundaries, and analytics.

## Flows that make sense

- Authentication is coherent end to end. Registration, verification, login, refresh, password reset, profile editing, and role-based landing pages align across docs, API, and web app (`docs/API_CONTRACTS.md:77-276`, `services/auth/app/api/v1/auth.py:57-321`, `apps/web/src/features/auth/AuthPages.tsx:95-345`, `apps/web/src/lib/session.ts:113-123`).

- Admin user management is a real product flow. Admins can list users, assign/remove roles, activate/deactivate accounts, review instructor applications, and access those screens through route guards (`services/auth/app/api/v1/admin.py:49-204`, `apps/web/src/features/admin/AdminPages.tsx:42-303`, `apps/web/src/app/router.tsx:135-145`).

- Instructor authoring is well connected. The app supports draft creation, metadata editing, module CRUD, asset upload/delete, draft-content persistence, validation, and publish submission (`services/course/app/api/v1/courses.py:41-311`, `services/course/app/api/v1/modules.py:39-145`, `services/course/app/api/v1/assets.py:53-163`, `apps/web/src/features/courses/CoursePages.tsx:148-323`, `apps/web/src/features/courses/CoursePages.tsx:643-1437`).

- The publishing pipeline is one of the clearest product stories in the repo. The backend exposes create/status/retry/approve/reject/cancel/activate operations, and the editor surfaces those states with understandable progress and action affordances (`docs/API_CONTRACTS.md:587-657`, `services/publishing/app/api/v1/versions.py:50-365`, `services/publishing/app/services/version_service.py:42-250`, `apps/web/src/features/courses/CoursePages.tsx:457-611`, `apps/web/src/features/courses/CoursePages.tsx:1320-1433`).

- Student enrollment to progress to certificate issuance is mostly coherent. Students can view a course, enroll, open a learning workspace, mark modules complete, see dashboard progress, and receive a certificate when completion criteria are met (`services/enrollment/app/api/v1/enrollments.py:34-240`, `services/progress/app/api/v1/progress.py:31-107`, `services/progress/app/services/progress_service.py:80-169`, `apps/web/src/features/courses/StudentCoursePage.tsx:205-259`, `apps/web/src/features/learning/LearningPages.tsx:307-662`).

- Public certificate verification makes sense and is intentionally exposed as a public route, which is a strong product detail for a credentialed learning platform (`apps/web/src/app/router.tsx:91-96`, `services/progress/app/api/v1/progress.py:96-107`, `apps/web/src/features/learning/LearningPages.tsx:631-662`).

- AI is productized, not just scaffolded. There is a learner assistant with citations plus instructor enhancement jobs and streaming, and both are wired into the first-party UI (`services/ai/app/api/v1/ask.py:46-159`, `services/ai/app/api/v1/instructor.py:47-274`, `apps/web/src/features/ai/AIPanels.tsx:78-715`).

- Admin ops are plausible as an internal console. Workflow inspection, retry, DLQ replay, and audit-log views all exist as product surfaces, not just backend utilities (`services/auth/app/api/v1/admin.py:207-338`, `apps/web/src/features/admin/AdminPages.tsx:387-897`).

## Flows that do not yet make sense

- The public catalog funnel breaks at the moment of interest. Public users can browse `/catalog`, but result cards link to `/app/catalog/:courseId`, and that route only exists inside the authenticated shell. There is no public course detail route, so anonymous discovery becomes a forced login wall before a user can inspect a course (`apps/web/src/features/catalog/CatalogPages.tsx:9-22`, `apps/web/src/app/router.tsx:91-96`, `apps/web/src/app/router.tsx:109-147`).

- Enrolled learners cannot actually download course materials. Both the catalog detail page and the learning workspace present downloadable assets to students, but `AssetService.presigned_download()` only allows the course owner or an admin. That makes the learning flow look available in the UI while the backend blocks it (`apps/web/src/features/courses/StudentCoursePage.tsx:33-69`, `apps/web/src/features/learning/LearningPages.tsx:485-545`, `services/course/app/services/asset_service.py:100-118`, `docs/API_CONTRACTS.md:567-578`).

- Instructors lose a clear product home for published courses. The default instructor landing page is `/app/courses`, but the workspace only queries courses with `visibility: 'DRAFT'`. Once a course is activated and becomes `PUBLISHED`, it disappears from "My Courses" even though publishing, analytics, and enrollments still matter most at that point (`apps/web/src/lib/session.ts:118-120`, `apps/web/src/features/courses/CoursePages.tsx:157-168`, `services/course/app/services/course_service.py:209-214`).

- There is no meaningful post-publish authoring journey. The backend correctly prevents editing non-draft courses, but the app does not offer "create new draft from live course", duplicate live course, or a visible version-history management flow for instructors. The publishing model is versioned, but the authoring UX ends at activation (`services/course/app/services/course_service.py:111-119`, `services/course/app/services/course_service.py:145-156`, `services/course/app/services/asset_service.py:141-149`, `services/publishing/app/api/v1/versions.py:309-338`).

- Notifications are implemented in backend but absent in product reality. The notification service supports listing, marking read, reading all, and persisted preferences, yet the notifications page is static and settings explicitly tell users preferences are not persisted. That is a UX trust problem, not just unfinished polish (`services/notification/app/api/v1/notifications.py:30-96`, `services/notification/app/services/notification_service.py:30-123`, `apps/web/src/features/notifications/NotificationsPage.tsx:1-23`, `apps/web/src/features/settings/SettingsPage.tsx:1-62`).

- The admin enrollment experience invents an approval flow that the domain does not have. The admin dashboard highlights "Enrollment approvals" and queries `PENDING` enrollments, but the enrollment model only supports `ENROLLED`, `COMPLETED`, and `CANCELLED`. The admin table also renders `ACTIVE` and `PENDING` badges even though those are not valid stored states (`apps/web/src/features/admin/AdminPages.tsx:707-710`, `apps/web/src/features/admin/AdminPages.tsx:762-767`, `apps/web/src/features/admin/AdminPages.tsx:839-880`, `services/enrollment/app/models/enrollment.py:18-37`, `services/enrollment/app/services/enrollment_service.py:113-143`).

- Instructor course-enrollment viewing is not ownership-scoped. The route and UI present course enrollments as an instructor-owned operational view, but the backend endpoint only checks that the caller has the `instructor` or `admin` role, then returns enrollments for any course ID. That makes the product logic and permissions model inconsistent (`apps/web/src/features/courses/CoursePages.tsx:1446-1537`, `services/enrollment/app/api/v1/enrollments.py:134-169`, `services/enrollment/app/repositories/enrollment_repository.py:90-113`).

- The applicant-side instructor journey stops after submission. Students can apply from Profile and admins can review applications, but applicants cannot see current status, past applications, rejection reason, or next steps on their own side (`apps/web/src/features/profile/ProfilePage.tsx:189-221`, `services/auth/app/api/v1/auth.py:294-321`, `services/auth/app/api/v1/admin.py:141-204`, `services/auth/app/services/instructor_application_service.py:28-134`).

- Dashboard navigation does not consistently move learners back into the right course. "In progress" cards link to `/app/learning`, not to a specific enrollment, so the dashboard surfaces progress but does not directly resume the exact learning session it previews (`apps/web/src/features/learning/LearningPages.tsx:53-70`, `apps/web/src/features/learning/LearningPages.tsx:214-241`).

- The home page markets organization and team-management value that the actual product model does not support. It promises organisations can track teams and own analytics, but there is no org, team, tenant, workspace, or enterprise admin model in docs routes or service code (`apps/web/src/features/home/HomePage.tsx:74-93`, `apps/web/src/features/home/HomePage.tsx:106-148`, `docs/API_CONTRACTS.md:77-1238`).

## Cross-flow inconsistencies

- The analytics product definition diverges across docs, backend, and frontend. The docs describe rich nested metrics and timeseries; the backend returns a small flat KPI object; the admin UI is built around the flat version. That changes what questions the product can answer and what users should expect (`docs/API_CONTRACTS.md:1120-1189`, `services/analytics/app/schemas/analytics.py:9-32`, `services/analytics/app/services/analytics_service.py:56-92`, `apps/web/src/features/admin/AdminPages.tsx:305-385`).

- The frontend route docs are behind the actual app. `FRONTEND.md` still frames catalog/search as placeholders and lists a much narrower protected route set, while the router now includes dashboard, learning player, certificates, notifications, settings, admin analytics, workflows, DLQ, and more (`docs/FRONTEND.md:46-73`, `apps/web/src/app/router.tsx:87-150`).

- AI entitlement policy is inconsistent with the architecture docs. The architecture says content access should require enrollment, admin, or instructor-owner. The actual AI service only blocks unenrolled students; instructors can query any published course because non-student callers skip the enrollment gate (`docs/ARCHITECTURE.md:276-281`, `services/ai/app/services/qa_graph.py:160-221`, `services/course/app/services/course_service.py:281-289`).

- Enrollment terminology is inconsistent across the product. The backend stores `ENROLLED`, the student experience talks about active learning, the instructor enrollments page relabels `ENROLLED` to `Active`, and the admin UI mixes in nonexistent `ACTIVE` and `PENDING` states. The same object carries different mental models depending on screen (`services/enrollment/app/models/enrollment.py:18-37`, `apps/web/src/features/courses/CoursePages.tsx:1482-1524`, `apps/web/src/features/admin/AdminPages.tsx:853-883`).

- Completion logic and UI copy are slightly out of sync. Progress initialization only creates rows for required modules, but the learner page says "you'll receive your certificate automatically" after working through "each module," which implies all visible modules matter equally. The actual product rule is closer to "required modules drive completion" (`services/progress/app/services/progress_service.py:192-205`, `apps/web/src/features/learning/LearningPages.tsx:381-382`, `docs/API_CONTRACTS.md:788-803`).

- Search language is broader than actual behavior. The top bar invites users to "Search courses, enrollments..." but clicking it only routes to course search. There is no cross-domain search for enrollments, notifications, or admin objects (`apps/web/src/components/navigation/TopBar.tsx:19-22`, `apps/web/src/features/catalog/CatalogPages.tsx:88-155`).

- The publishing story in docs is simpler than the implemented product. Phase and API docs describe publish-to-ready, but the implemented system adds a meaningful approval gate plus a separate activation step before the course becomes live. The UI reflects that, but the docs only partially do (`docs/PHASES.md:391-485`, `docs/API_CONTRACTS.md:587-657`, `services/publishing/app/services/version_service.py:42-250`, `apps/web/src/features/courses/CoursePages.tsx:1362-1423`).

## Obvious overlooked features

- A public course detail page that preserves the discovery funnel.

- A persistent instructor "live courses" area separate from drafts.

- A "create new draft/version from published course" flow.

- Applicant self-service for instructor-application status and outcome.

- A real notifications inbox and persisted preferences UI using the APIs that already exist.

- Instructor-facing course analytics in the web app. The backend exposes per-course analytics, but there is no instructor product surface for it (`services/analytics/app/api/v1/analytics.py:37-49`).

- Clear prerequisite messaging by course title, not opaque IDs, when enrollment fails (`docs/API_CONTRACTS.md:65-67`, `services/course/app/services/course_service.py:247-264`).

- Direct "resume this course" navigation from the learner dashboard to a specific enrollment.

- Better explanation of what activation means after a version reaches `READY`, since publish completion and going live are separate steps in the actual system (`services/publishing/app/api/v1/versions.py:309-338`, `apps/web/src/features/courses/CoursePages.tsx:597-602`).

- If the marketing copy stays organization-focused, an actual org/team/workspace model.

## Suggested product priorities

1. Fix the broken learning entitlement first.
   Let enrolled students download their course assets or remove those affordances until that rule is implemented.

2. Repair the anonymous catalog funnel.
   Add a public course detail route or stop linking anonymous users into a protected detail page.

3. Give instructors a post-publish home.
   Separate drafts from live courses, show active versions, and make analytics/enrollments reachable from that surface.

4. Add a true re-versioning journey.
   Versioned publishing is not product-complete until an instructor can start the next revision from a live course.

5. Replace notification placeholders with the real product.
   The APIs and persistence are already present; the web app is what is missing.

6. Align ownership and admin semantics.
   Course-enrollment views should enforce instructor ownership, and the admin UI should stop implying nonexistent enrollment approval states.

7. Decide the real AI entitlement rule.
   Either allow instructors to query any public course intentionally and document it, or restrict AI to owner/admin/enrolled-user as the architecture says.

8. Normalize analytics into one contract.
   Pick the rich metrics model or the flat KPI model and make docs, backend, and UI agree.

9. Add applicant-side visibility for instructor applications.
   Submission should not become a black box from the applicant's perspective.

10. Tighten product-facing docs to match the shipped app.
    `FRONTEND.md` and parts of `API_CONTRACTS.md` currently make the product look different from what users and developers actually get.

## Risks/assumptions

- This review is grounded in repository docs and source code, not a fully exercised running stack, so some runtime integrations could differ.

- I ignored `.venv` and generated files as requested.

- I treated the first-party web app as the main product surface and judged coherence based on visible routes, copy, and server behavior behind those routes.

- Where docs and code differ, I treated that as a product risk because users, PMs, and engineers will form expectations from both.

- Some gaps may be intentional phase lag rather than mistakes, but they are still confusing when the current app surface already exposes those journeys.

## Strongest findings

- Anonymous users can browse the catalog but cannot open a course detail page without being forced into auth because result cards point to a protected route.

- Enrolled learners are shown downloadable study materials in the UI, but the backend denies student asset downloads entirely.

- Instructors have a strong draft workflow, then lose visibility of their own course once it becomes `PUBLISHED` because "My Courses" only shows drafts.

- The product uses versioned publishing, approval, and activation, but there is still no instructor-friendly way to start the next revision from a live course.

- Notifications and notification preferences are real backend features but still presented as placeholders or non-persistent settings in the app.

- The admin UI suggests enrollment approvals and `PENDING`/`ACTIVE` enrollment states that do not exist in the actual enrollment domain.

- Any instructor appears able to inspect enrollments for any course ID, which conflicts with the product's ownership model.

- The AI entitlement rule implemented in code is looser than the architecture says for instructors.

- Analytics are materially different depending on whether you read the docs, backend schema, or admin UI.

- Instructor applicants can submit requests, but there is no self-serve way to see status, outcome, or next steps afterward.

- The marketing site overpromises organization/team capabilities that the product model does not implement.

File written: yes (`/home/kali/proj/educorp/reports/user-flow-report.md`).
