# Phase 3 Overhaul - Phase 1 Foundation

## Objective

Replace the current mutable, direct publish start with an immutable snapshot and a human-reviewed preflight stage.

When this phase is complete, a publish request must no longer depend on reading live draft state during workflow execution. The publishing service must work from a version manifest that is frozen at publish start.

## Target Outcome

- A publish action creates a new version and an immutable manifest snapshot.
- Temporal receives `version_id` and small control payloads only.
- Publishing no longer writes directly into `course.courses` through raw SQL.
- A human can inspect a preflight bundle before actual extraction and indexing starts.

## Architecture Decisions

### Service Boundaries

- Course service remains the authoring source of truth.
- Publishing service becomes the source of truth for publish versions, manifests, artifacts, step tracking, and activation state.
- Search service remains read-only in this phase.

### Publish Flow Shape

1. User clicks publish in the course UI.
2. Course service validates the draft and assembles a publish snapshot.
3. Course service sends that snapshot to publishing service.
4. Publishing service persists the immutable manifest and starts a Temporal workflow with `version_id`.
5. Workflow runs preflight only, then pauses in `REVIEW_REQUIRED`.
6. Human reviews the preflight bundle and approves or rejects it.

### Version Status Model

Use these top-level version statuses:

- `PREPARING`
- `REVIEW_REQUIRED`
- `PUBLISHING`
- `READY`
- `FAILED`
- `CANCELLED`
- `SUPERSEDED`

Keep detailed progress in `publishing_steps`. Do not overload the top-level version status with too much meaning.

## Local Operator Setup

### Required Local Secrets

Put these only in the local `.env` file. Do not commit them.

```bash
NANOGPT_BASE_URL=https://nano-gpt.com/api/v1
NANOGPT_API_KEY=<set locally>
NANOGPT_MODEL=google/gemma-4-31b-it

OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=<set locally>
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSION=1536
```

### Existing Dev Infrastructure

- MinIO console: http://localhost:9001
- MinIO credentials: `educorp` / `educorp_dev`
- MinIO bucket: `course-assets`
- Temporal UI: http://localhost:8088
- Qdrant API: http://localhost:6333

## Deliverables

### Data Model Deliverables

Add or refactor these publishing tables:

- `publishing.course_versions`
  - keep `course_id`, `version_number`, and timestamps
  - add `status`, `approval_state`, `manifest_hash`, `preflight_summary_json`, `activated_at`, `superseded_at`
- `publishing.version_manifests`
  - one row per publish version
  - stores normalized course metadata snapshot
- `publishing.version_manifest_modules`
  - module order and module-level metadata snapshot
- `publishing.version_manifest_assets`
  - asset metadata snapshot, file hash, storage path, source MIME type, page estimate if available
- `publishing.version_artifacts`
  - artifact registry for manifest JSON, review bundle JSON, future OCR outputs, chunk JSON, and reports

### MinIO Layout Deliverables

Keep the existing bucket but switch to a predictable prefix layout:

```text
course-assets/
  raw/<sha256>
  versions/<version_id>/manifest/manifest.json
  versions/<version_id>/review/preflight.json
  versions/<version_id>/review/flags.json
  versions/<version_id>/artifacts/
```

Rules:

- Raw asset objects are immutable.
- Version artifacts are namespaced by `version_id`.
- The manifest hash must match the stored manifest JSON.

### API Deliverables

Add or refactor these API contracts:

- Course service:
  - keep `POST /api/v1/courses/{course_id}/publish`
  - add internal publish snapshot assembler used by the publish route
  - add internal activation endpoint for publishing service
- Publishing service:
  - `POST /api/v1/publishing/versions`
  - `GET /api/v1/publishing/versions/{version_id}`
  - `POST /api/v1/publishing/versions/{version_id}/approve`
  - `POST /api/v1/publishing/versions/{version_id}/reject`
  - keep retry and cancel, but make them operate on manifest-driven versions

### Frontend Deliverables

Update the existing course publishing UI to show:

- preflight status
- estimated work summary
- flagged assets count
- explicit approve and reject controls
- version manifest summary link

## Exact Implementation Sequence

### Step 1.1 - Fix configuration naming

- Update `.env.example`.
- Replace vague provider names with explicit NanoGPT and OpenAI fields.
- Remove outdated embedding defaults such as `text-embedding-ada-002` from the overhaul path.

### Step 1.2 - Add new publishing schema objects

- Create a new Alembic migration in `services/publishing/alembic/versions/`.
- Add manifest and artifact tables.
- Backfill `course_versions` with fields required for review and activation.

### Step 1.3 - Build the snapshot assembler in course service

- Refactor publish initiation logic so course service creates a normalized snapshot object.
- Include course metadata, modules in order, assets in order, asset types, file names, storage paths, and content hashes.
- Fail publish start if any required hash or upload state is missing.

### Step 1.4 - Persist immutable publish manifests

- Publishing service stores the manifest in Postgres.
- Publishing service also writes the manifest JSON to MinIO under `versions/<version_id>/manifest/manifest.json`.
- Compute and persist `manifest_hash`.

### Step 1.5 - Refactor workflow inputs

- `PublishCourseWorkflow` receives `version_id` and control flags only.
- Activity inputs become `version_id`, `manifest_asset_id`, or `artifact_id`.
- Remove workflow payload patterns that pass extracted text, chunk arrays, or embedding arrays between activities.

### Step 1.6 - Add the preflight activity

The preflight activity must:

- confirm every asset object exists in MinIO
- verify every asset has a stable file hash
- compute a rough page estimate where possible
- detect likely image-heavy PDFs using quick heuristics
- produce a preflight JSON bundle and register it in `publishing.version_artifacts`

### Step 1.7 - Pause for human approval

- When preflight succeeds, version status becomes `REVIEW_REQUIRED`.
- The UI must show the review state.
- Approval resumes the workflow.
- Rejection leaves the version in `CANCELLED` or a new rejected substate stored in approval metadata.

### Step 1.8 - Remove cross-schema direct writes from publishing

- Publishing service must stop updating `course.courses` through raw SQL.
- Activation later must happen through a course service internal endpoint.

### Step 1.9 - Preserve the existing user touchpoint

- Keep the publish action in `apps/web/src/features/courses/CoursePages.tsx`.
- Replace the current direct status assumptions with manifest-aware preflight status rendering.

### Step 1.10 - Add tests before moving to Phase 2

Required tests for Phase 1:

- snapshot immutability test
- manifest hash test
- approval gate test
- retry-on-same-manifest test
- edit-draft-after-publish test

## Files Expected To Change

Core files likely to change in this phase:

- `services/course/app/api/v1/courses.py`
- `services/course/app/services/publishing_client.py`
- `services/course/app/services/course_service.py`
- `services/course/app/schemas/publishing.py`
- `services/publishing/app/api/v1/versions.py`
- `services/publishing/app/services/version_service.py`
- `services/publishing/app/workflows/publish_course.py`
- `services/publishing/app/workflows/types.py`
- `services/publishing/app/activities/publishing_activities.py`
- `services/publishing/app/models/*.py`
- `services/publishing/app/repositories/*.py`
- `services/publishing/app/config.py`
- `apps/web/src/features/courses/CoursePages.tsx`
- `apps/web/src/lib/api.ts`
- `.env.example`

## Manual Validation Gate

Do not start Phase 2 until every item below passes.

### Validation A - Stack and provider configuration

```bash
bash -c "cd /home/kali/proj/educorp && docker compose --profile workflow --profile app up -d"
```

Check these manually:

- MinIO console opens at http://localhost:9001
- Temporal UI opens at http://localhost:8088
- `course-assets` bucket exists
- local `.env` contains NanoGPT and OpenAI secrets, but git has no tracked secret change

### Validation B - Immutable manifest proof

1. Create or select a draft course.
2. Start publish.
3. Before approval, edit the draft title or module order.
4. Refresh the publish review screen.
5. Confirm the manifest view still shows the original title and original module order.

### Validation C - MinIO artifact proof

Optional CLI check if `mc` is installed:

```bash
bash -c "mc alias set local http://localhost:9000 educorp educorp_dev && mc tree local/course-assets/versions"
```

Confirm the new version folder contains at least:

- `manifest/manifest.json`
- `review/preflight.json`

### Validation D - Approval gate proof

1. Confirm the version status is `REVIEW_REQUIRED` before any extraction starts.
2. Approve the version.
3. Confirm the workflow resumes.
4. Cancel another version in review state and confirm no activation occurs.

## Exit Criteria

- Publish start produces an immutable manifest every time.
- Workflow payloads are reduced to IDs and small control objects.
- Preflight review exists and is human-visible.
- Publishing no longer directly mutates course tables through raw SQL.
- Required Phase 1 tests exist and pass.

## Rollback Rule

If Phase 1 causes instability, keep the old publish route disabled behind a feature flag. Do not delete old paths until the new manifest-based flow passes the full validation gate.
