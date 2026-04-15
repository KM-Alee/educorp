# Phase 3 Overhaul - Phase 3 Search, Activation, And End-To-End Proof

## Objective

Make the new publishing pipeline operationally complete.

This phase activates reviewed versions, upgrades search, hardens the operator workflow, and proves the full system by publishing a real course from `dummy-course/` with an AI agent and human review.

## Target Outcome

- Reviewed versions become active only after explicit approval.
- Search results only expose active, approved content.
- Semantic results carry reliable page or slide citations.
- The operator can review, retry, cancel, and inspect cleanup status.
- The repo has an end-to-end publish run defined for real dummy-course PDFs.

## Architecture Decisions

### Activation Rules

- `PUBLISHING` does not mean user-visible.
- A version becomes user-visible only after activation.
- Activation must happen after:
  - chunking success
  - embeddings success
  - Qdrant indexing success
  - operator approval of any low-confidence review bundle

### Search Rules

- Search service serves keyword and semantic search.
- Publishing service remains the writer to Qdrant.
- Search service only queries active versions.
- Search service must not read superseded content.

### Metadata Model For Search

Add a search-local catalog table or projection that contains:

- `course_id`
- `active_version_id`
- `title`
- `short_description`
- `category`
- `difficulty`
- `tags`
- `instructor_display_name`
- `activated_at`

This keeps keyword search simple and avoids fragile cross-service reads.

## Deliverables

### Backend Deliverables

- activation endpoint between publishing and course service
- search projection sync or activation sync path
- PostgreSQL full-text keyword search
- semantic search responses with page or slide citation fields
- cleanup job for superseded vectors and temporary artifacts
- failure and approval audit trail for each version

### Frontend Deliverables

- upgraded publishing panel with review summary, approval state, and final activation state
- catalog UI that reflects only active approved versions
- clearer search result citations

### Testing Deliverables

- activation correctness tests
- keyword search ranking tests
- semantic citation tests
- retry and cancel operational tests
- full dummy-course publish runbook

## Exact Implementation Sequence

### Step 3.1 - Add activation handshake

- Publishing service calls a course service internal endpoint to activate the approved version.
- Course service updates `current_version_id` and visible publish state.
- Do not reactivate through direct SQL from publishing.

### Step 3.2 - Add search metadata sync

Use one of these approaches, but keep it simple:

- preferred: publishing service calls search service internal sync endpoint on activation
- acceptable fallback: search service reads an activation-safe projection table in Postgres

Do not wait for Kafka to make the core activation path correct.

### Step 3.3 - Upgrade keyword search

- move from `ILIKE` heuristics to PostgreSQL full-text search
- rank by title, short description, tags, and recency of activation
- filter to active versions only

### Step 3.4 - Upgrade semantic response format

Semantic search response must include:

- `chunk_id`
- `course_id`
- `version_id`
- `module_title`
- `asset_title`
- `page_or_slide_number`
- `chunk_index`
- `score`
- `quality_score`

### Step 3.5 - Add cleanup paths

- delete superseded version vectors after a retention window
- optionally delete rendered page images and OCR artifacts after a retention window
- keep manifests and quality reports for auditability

### Step 3.6 - Harden operator workflows

The UI must clearly show:

- review required
- approved
- publishing in progress
- ready but not activated
- activated
- failed with operator-readable reason

### Step 3.7 - Add an end-to-end runner for dummy-course

Create a script or guided agent workflow that:

1. creates a course shell
2. creates or reuses modules
3. uploads all PDFs from `dummy-course/`
4. validates the draft
5. starts publish
6. polls status until review or ready
7. approves if review is required and the operator accepts the flagged items
8. waits for activation
9. verifies search and Qdrant
10. prints a final report

### Step 3.8 - Add tests before declaring the overhaul complete

Required tests:

- activation does not expose unapproved versions
- superseded vectors are not returned in search
- keyword search only returns active versions
- semantic search includes valid page or slide citations
- cleanup job removes temporary artifacts and stale vectors as configured
- dummy-course script happy path works in a local stack

## Files Expected To Change

Core files likely to change in this phase:

- `services/course/app/api/v1/courses.py`
- `services/course/app/services/course_service.py`
- `services/publishing/app/api/v1/versions.py`
- `services/publishing/app/services/version_service.py`
- `services/search/app/api/v1/search.py`
- `services/search/app/services/keyword_search_service.py`
- `services/search/app/services/semantic_search_service.py`
- `services/search/app/repositories/*.py`
- `services/search/app/schemas/search.py`
- `services/search/alembic/versions/*.py`
- `apps/web/src/features/courses/CoursePages.tsx`
- `apps/web/src/features/catalog/CatalogPages.tsx`
- `apps/web/src/lib/api.ts`
- `scripts/phase3_dummy_course_publish.py`

## Manual Validation Gate

This is the final gate. Nothing is considered complete until this full run passes.

### Validation A - Activation proof

1. Publish a version and stop before approval.
2. Confirm the course is still not live in the catalog.
3. Approve and activate the version.
4. Confirm the course now appears in the catalog.

### Validation B - Search proof

Run keyword search and semantic search after activation.

Keyword search should return only the active approved course.

Semantic search results must show:

- correct module title
- correct asset title
- correct page or slide number

### Validation C - Superseded version proof

1. Publish a second version of the same course.
2. Activate it.
3. Confirm search never returns chunks from the older superseded version.

### Validation D - Cleanup proof

1. Trigger the cleanup job.
2. Confirm stale vectors for superseded versions are removed.
3. Confirm manifests and reports remain available.

## Generate A Course

This section is mandatory. It is the final proof that the overhaul works on real inputs.

### Human Preparation

Put the real lecture PDFs in:

```text
/home/kali/proj/educorp/dummy-course/
```

Current folder examples already present:

- `Lecture 7-Javascript.pdf`
- `Lecture 8-Javascript.pdf`
- `Lecture 9 Javascript.pdf`

### Required Agent Goal

After the Phase 3 implementation exists, run an AI agent with the following mission:

1. create a course titled `JavaScript Foundations From Slides`
2. create modules in lecture order based on sorted filenames in `dummy-course/`
3. upload each PDF to the matching module
4. run draft validation
5. start publish
6. pause for human review if the version enters `REVIEW_REQUIRED`
7. approve the version if the review bundle looks acceptable
8. wait until the version is activated
9. run keyword search for `javascript`
10. run a semantic search query that should hit one of the uploaded lectures
11. produce a report with version ID, total chunks, OCR pages, NanoGPT pages, Qdrant point count, and any warnings

### Suggested Agent Prompt

```text
Use the live EduCorp stack in /home/kali/proj/educorp. Create an instructor course named JavaScript Foundations From Slides from the PDFs in dummy-course/. Use lecture-order module names based on the filenames. Upload the files, validate the draft, start publish, wait for review if needed, ask for approval only if a human decision is required, finish activation, then verify keyword and semantic search. Return a final structured report with course_id, version_id, activated_at, total_assets, total_chunks, OCR pages used, NanoGPT pages used, Qdrant point count, and any failure or quality warnings.
```

### Human Final Review Checklist

The human operator must manually verify all of the following after the agent run:

- the course exists in the UI
- all lecture PDFs are visible in the course
- the version is activated, not just published
- MinIO contains the manifest, quality report, and chunk artifacts
- Qdrant contains points for the active version only
- keyword search returns the course
- semantic search returns chunks with correct page or slide citations
- the final agent report matches the actual system state

## Exit Criteria

- Activation is explicit and correct.
- Search returns only active approved versions.
- Semantic results carry good provenance.
- Cleanup exists for stale vectors and temporary artifacts.
- The dummy-course end-to-end publish run succeeds.
- Required Phase 3 tests exist and pass.
