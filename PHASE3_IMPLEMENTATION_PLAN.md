# EduCorp — Phase 3 Implementation Plan

## Goal

Deliver a production-shaped publishing pipeline that turns a validated draft course into a searchable, READY course version. The outcome for Phase 3 is not just an endpoint that says "publishing started"; it is an end-to-end workflow with durable status tracking, search indexing, and an operator-friendly surface in the web app.

## Current Starting Point

- Phase 2 already provides draft course CRUD, module CRUD and ordering, asset storage in MinIO, draft validation, and Mongo-backed draft content.
- The first-party web app can now exercise the authoring workflow from `/app/courses` and `/app/courses/:courseId`.
- The main missing capabilities for Phase 3 are versioning, orchestration, extraction/chunking, embedding/indexing, and search/catalog delivery.

## Design Decisions

- Use the course service as the source of truth for draft validation and version creation, but keep workflow orchestration in the publishing service.
- Treat publishing as an idempotent state machine keyed by course version, not as an ad hoc fire-and-forget task.
- Keep text extraction and embedding generation in explicit Temporal activities so retries, cancellation, and observability stay first-class.
- Make PostgreSQL the source of truth for version metadata and publishing progress; use Qdrant as a derived index only.
- Add the web track in lockstep: publishing status and catalog/search views should ship with the backend path, not later.

## Workstreams

### 1. Data model and contracts

- Add `course_versions`, `publishing_steps`, and `chunks` models plus migrations.
- Define version lifecycle states such as `DRAFT`, `PUBLISHING`, `READY`, `FAILED`, and `CANCELLED`.
- Add response schemas for publish requests, version status, retry, cancel, and catalog/search results.
- Update `docs/API_CONTRACTS.md`, `docs/DATA_MODELS.md`, and `docs/PHASES.md` as each contract stabilizes.

### 2. Publishing orchestration

- Implement a `PublishCourseWorkflow` in the publishing service.
- Create activities for asset validation, text extraction, chunking, embedding generation, Qdrant indexing, and finalization.
- Persist step-level progress so status APIs do not depend solely on Temporal history.
- Make retries idempotent at the version level and ensure cancellation leaves the version in a coherent state.

### 3. Extraction and indexing pipeline

- Add extractor adapters for PDF, DOCX, PPTX, TXT, VTT, and SRT.
- Normalize extracted text and attach stable metadata: course, module, asset, chunk position, and version.
- Batch embedding calls behind a provider abstraction compatible with the existing OpenAI-compatible stack.
- Create the Qdrant collection and payload indexes during service startup or a controlled bootstrap step.

### 4. Search and catalog delivery

- Expose browseable catalog endpoints over READY courses only.
- Implement keyword search first in PostgreSQL over course metadata.
- Add semantic search over Qdrant-backed chunks for the search service once the indexing pipeline is stable.
- Return version-aware metadata so the frontend and future AI surfaces can explain what is searchable.

### 5. Frontend track

- Add a publish action to the course editor with explicit validation feedback.
- Add a publishing status view with per-step progress and failure messaging.
- Add catalog and search routes that use READY course data only.
- Keep the UI operational: status, failures, retry, and cancel should be legible without opening Temporal.

## Execution Sequence

### Milestone 1: Versioning foundation

- Add models, migrations, repositories, and schemas.
- Implement `POST /courses/{id}/publish` to create a version record and start a workflow stub.
- Implement `GET /publishing/versions/{version_id}` against stored step rows.
- Verify with backend tests and a manual publish smoke path.

### Milestone 2: Real workflow activities

- Add asset validation and extraction activities first.
- Add chunking and embedding generation next.
- Add Qdrant indexing and finalization last.
- Verify each activity in isolation, then the composed workflow with mocked external dependencies.

### Milestone 3: Search and catalog

- Implement catalog browse against READY versions.
- Implement metadata keyword search.
- Implement semantic retrieval in the search service.
- Verify catalog/search correctness with seeded data and integration tests.

### Milestone 4: Web completion and hardening

- Ship publish/status/catalog/search routes in `apps/web`.
- Add retry and cancel controls for failed or in-flight publishing jobs.
- Add route, API, and happy-path authoring-to-publish frontend tests.

## Testing Strategy

- Unit test extractors, chunking, state transitions, and embedding batching.
- Integration test publish endpoint, version persistence, and workflow status mapping.
- Mock embedding providers and Qdrant in service-level tests.
- Add at least one full publish happy path behind a lightweight local stack or high-fidelity mocks.
- Confirm Phase 3 coverage stays above the project threshold before starting Phase 4.

## Risks and Mitigations

- Text extraction libraries vary by file type.
Mitigation: isolate them behind small activity adapters and normalize outputs early.

- Embedding calls can be slow or rate-limited.
Mitigation: batch requests, persist progress between steps, and make retries idempotent.

- Search can drift from source-of-truth course state.
Mitigation: only surface READY versions and finalize version activation in one explicit step.

- Workflow observability can become opaque if status only lives in Temporal.
Mitigation: persist step rows and expose them directly in the API and web UI.

## Exit Criteria

- An instructor can publish a validated draft from the web app.
- A version transitions from `PUBLISHING` to `READY` with durable step tracking.
- READY courses appear in catalog browse and keyword search.
- Semantic chunks are indexed in Qdrant with course/module/asset metadata.
- Failed publishes are inspectable and retryable without manual database intervention.