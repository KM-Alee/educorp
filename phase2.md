# Phase 2 Implementation Plan

## Goal

Deliver Phase 2 for EduCorp: instructors can create and manage draft courses, add and reorder modules, upload and manage assets in MinIO, persist rich draft content in MongoDB, and validate drafts before Phase 3 publishing.

This plan is based on the current repository state on 2026-04-13:

- Phase 0 infrastructure is present and wired through Docker Compose.
- Phase 1 auth is materially implemented and provides the role and JWT patterns to reuse.
- The course service is still a scaffold: [services/course/app/main.py](services/course/app/main.py), [services/course/app/config.py](services/course/app/config.py), [services/course/app/dependencies.py](services/course/app/dependencies.py), and [services/course/app/api/v1/__init__.py](services/course/app/api/v1/__init__.py) only expose service startup and health routes.
- The course service already declares the right external dependencies in [services/course/pyproject.toml](services/course/pyproject.toml): `motor` and `miniopy-async`.
- Infra and environment support for MongoDB and MinIO already exist in [docker-compose.yml](docker-compose.yml) and [.env.example](.env.example).
- The course Alembic setup exists, but [services/course/alembic/versions](services/course/alembic/versions) is empty.

## Context Map

### Files To Modify

| File | Purpose | Planned Change |
|------|---------|----------------|
| [services/course/app/config.py](services/course/app/config.py) | Course service settings | Add MongoDB, MinIO, upload, and validation settings. |
| [services/course/app/dependencies.py](services/course/app/dependencies.py) | DI entrypoint | Add Mongo client, Mongo database, MinIO client, and optional file-validation helpers. |
| [services/course/app/api/v1/__init__.py](services/course/app/api/v1/__init__.py) | API router root | Keep health routes and include course, module, and asset routers. |
| [services/course/app/models/__init__.py](services/course/app/models/__init__.py) | Model exports | Export `Course`, `Module`, and `Asset`. |
| [services/course/tests/conftest.py](services/course/tests/conftest.py) | Test setup | Add DB/session overrides, mocked auth context, Mongo/MinIO fakes, and file fixtures. |
| [services/course/alembic/env.py](services/course/alembic/env.py) | Migration metadata | Verify metadata discovery once course models are added. |

### Files To Add

| File | Purpose |
|------|---------|
| [services/course/app/models/course.py](services/course/app/models/course.py) | SQLAlchemy course aggregate root. |
| [services/course/app/models/module.py](services/course/app/models/module.py) | SQLAlchemy module entity. |
| [services/course/app/models/asset.py](services/course/app/models/asset.py) | SQLAlchemy asset entity. |
| [services/course/app/schemas/course.py](services/course/app/schemas/course.py) | Course request and response schemas. |
| [services/course/app/schemas/module.py](services/course/app/schemas/module.py) | Module request and response schemas. |
| [services/course/app/schemas/asset.py](services/course/app/schemas/asset.py) | Asset request and response schemas. |
| [services/course/app/schemas/common.py](services/course/app/schemas/common.py) | Shared paging, filters, and validation issue schemas for the service. |
| [services/course/app/repositories/course_repository.py](services/course/app/repositories/course_repository.py) | Course data access. |
| [services/course/app/repositories/module_repository.py](services/course/app/repositories/module_repository.py) | Module data access. |
| [services/course/app/repositories/asset_repository.py](services/course/app/repositories/asset_repository.py) | Asset data access. |
| [services/course/app/repositories/draft_content_repository.py](services/course/app/repositories/draft_content_repository.py) | MongoDB draft-content access. |
| [services/course/app/services/course_service.py](services/course/app/services/course_service.py) | Course CRUD, catalog, ownership checks, slug handling. |
| [services/course/app/services/module_service.py](services/course/app/services/module_service.py) | Module CRUD and reorder logic. |
| [services/course/app/services/asset_service.py](services/course/app/services/asset_service.py) | Upload, list, delete, and download flows. |
| [services/course/app/services/draft_validation_service.py](services/course/app/services/draft_validation_service.py) | Pre-publish validation rules. |
| [services/course/app/services/storage_service.py](services/course/app/services/storage_service.py) | MinIO adapter and storage-path conventions. |
| [services/course/app/services/slug_service.py](services/course/app/services/slug_service.py) | Deterministic slug generation and collision handling. |
| [services/course/app/api/v1/courses.py](services/course/app/api/v1/courses.py) | Course endpoints. |
| [services/course/app/api/v1/modules.py](services/course/app/api/v1/modules.py) | Module endpoints. |
| [services/course/app/api/v1/assets.py](services/course/app/api/v1/assets.py) | Asset endpoints. |
| [services/course/alembic/versions/0001_course_phase2.py](services/course/alembic/versions/0001_course_phase2.py) | Initial course schema migration. |
| [services/course/tests/unit/test_slug_service.py](services/course/tests/unit/test_slug_service.py) | Slug collision and formatting rules. |
| [services/course/tests/unit/test_draft_validation_service.py](services/course/tests/unit/test_draft_validation_service.py) | Draft validation logic. |
| [services/course/tests/unit/test_storage_service.py](services/course/tests/unit/test_storage_service.py) | MIME, magic-byte, checksum, and storage-path logic. |
| [services/course/tests/integration/test_course_api.py](services/course/tests/integration/test_course_api.py) | Course CRUD and catalog behavior. |
| [services/course/tests/integration/test_module_api.py](services/course/tests/integration/test_module_api.py) | Module CRUD and reorder behavior. |
| [services/course/tests/integration/test_asset_api.py](services/course/tests/integration/test_asset_api.py) | Upload, download, and delete behavior. |

### Dependencies To Reuse

| File | Pattern To Follow |
|------|-------------------|
| [services/auth/app/api/v1/auth.py](services/auth/app/api/v1/auth.py) | Thin route handlers, DI through `Depends`, commit at route boundary, `SuccessResponse` envelopes. |
| [services/auth/app/services/auth_service.py](services/auth/app/services/auth_service.py) | Service-layer orchestration with repositories and explicit business rules. |
| [services/auth/app/repositories/user_repository.py](services/auth/app/repositories/user_repository.py) | Async repository pattern using `flush()` and explicit query composition. |
| [shared/educorp_common/database/base.py](shared/educorp_common/database/base.py) | Base model mixins and UUID/timestamp conventions. |
| [shared/educorp_common/schemas/responses.py](shared/educorp_common/schemas/responses.py) | Standard success and paginated response envelopes. |

### Existing Tests And Gaps

| File | Current Coverage |
|------|------------------|
| [services/course/tests/conftest.py](services/course/tests/conftest.py) | Only ASGI app and client fixtures. |
| [services/auth/tests/unit/test_password.py](services/auth/tests/unit/test_password.py) | Example unit-test structure for service-local behavior. |
| [services/auth/tests/unit/test_jwt.py](services/auth/tests/unit/test_jwt.py) | Example unit-test structure for shared auth utilities. |

### Risk Assessment

- Breaking API changes: low, because the course API is not implemented yet.
- Database migration risk: medium, because Phase 2 introduces the first real schema in the course service.
- Configuration risk: medium, because MinIO and MongoDB client settings need to be surfaced in the course service.
- Cross-service coupling risk: medium, because course ownership and instructor authorization depend on Phase 1 JWT role claims without direct auth-schema joins.
- Test infrastructure risk: medium, because course tests currently lack DB, Mongo, and object-storage fakes.

## Phase 2 Scope Boundaries

### In scope

- Course CRUD in PostgreSQL.
- Module CRUD and module reorder in PostgreSQL.
- Asset upload, list, presigned download, and delete through MinIO.
- Draft-content persistence in MongoDB for rich module/course content.
- Draft validation rules needed before publishing.
- Ownership and role enforcement using existing JWT claims.
- Catalog stub behavior consistent with Phase 2 and compatible with Phase 3.
- Unit and integration tests for the above.

### Explicitly out of scope

- Temporal publishing workflow.
- Embedding generation, chunking, Qdrant indexing, or search indexing.
- Enrollment-aware download authorization beyond a minimal placeholder compatible with later phases.
- Notification, analytics, or outbox-based publish events.
- Major frontend authoring UI unless separately planned.

## Design Decisions To Lock Before Coding

1. Ownership model
   - Use `course.instructor_id = current_user.id` from JWT claims.
   - Enforce creation with `require_roles("instructor", "admin")` and edits with owner-or-admin checks in the service layer.

2. Catalog stub semantics
   - For anonymous and student callers, `GET /courses` should return only publishable content.
   - In Phase 2, because `current_version_id` is not populated yet, the public catalog may validly be empty.
   - Instructor and admin callers may query drafts using explicit visibility filters.

3. Rich content source of truth
   - PostgreSQL stores structure and metadata.
   - MongoDB stores rich draft payloads keyed by `course_id`, with nested module content blocks to support Phase 3 extraction later.

4. Asset policy
   - Allow only `pdf`, `docx`, `pptx`, `txt`, `md`, `vtt`, and `srt`.
   - Validate extension, MIME type, magic bytes where feasible, file size, and checksum.
   - Persist uploads to deterministic paths like `course-assets/{course_id}/{module_id}/{asset_id}/{sanitized_file_name}`.

5. Slug policy
   - Generate from title using a deterministic slugify function.
   - Resolve collisions by suffixing `-2`, `-3`, and so on.
   - Regenerate only when title changes.

## Workstream Plan

## Workstream 1: Data Model And Migration

### Deliverables

- SQLAlchemy models for `course.courses`, `course.modules`, and `course.assets` aligned with [docs/DATA_MODELS.md](docs/DATA_MODELS.md).
- Initial Alembic migration for the course schema and indexes.

### Steps

1. Add `Course`, `Module`, and `Asset` models using shared mixins and explicit `schema="course"` table args.
2. Define relationships only where they simplify loading and do not create hidden eager-load behavior.
3. Model enums as constrained strings to stay aligned with existing project style.
4. Create `0001_course_phase2.py` to create tables and indexes exactly once.
5. Ensure the migration is safe to run in clean environments and idempotent through Alembic history, not manual guards.

### Acceptance

- `alembic upgrade head` creates all three tables and indexes.
- Soft-delete is implemented for courses only.
- Unique constraints exist for `slug` and `(course_id, sort_order)`.

## Workstream 2: Service Configuration And Dependencies

### Deliverables

- Course-service settings for Mongo, MinIO, upload limits, and presigned URL TTL.
- Dependency providers for database session, Mongo database, and MinIO client.

### Steps

1. Extend [services/course/app/config.py](services/course/app/config.py) with fields for:
   - `mongo_url`
   - `mongo_db`
   - `minio_endpoint`
   - `minio_access_key`
   - `minio_secret_key`
   - `minio_bucket`
   - `minio_use_ssl`
   - `max_asset_size_bytes`
   - `presigned_url_ttl_seconds`
2. Update [services/course/app/dependencies.py](services/course/app/dependencies.py) to initialize and expose:
   - async Mongo client
   - Mongo database handle
   - MinIO client
3. Close Mongo and MinIO-related clients cleanly in lifespan shutdown if long-lived clients are retained.
4. Keep settings names consistent with [.env.example](.env.example) to avoid new env drift.

### Acceptance

- The course service can connect to PostgreSQL, MongoDB, and MinIO from Docker.
- Local tests can override these providers without patching globals in arbitrary modules.

## Workstream 3: Schemas And API Contracts

### Deliverables

- Pydantic v2 request and response schemas matching [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md).
- Pagination and validation-issue schemas for future reuse.

### Steps

1. Create request models for course create/update, module create/update/reorder, and asset upload metadata.
2. Create response models for course detail, course list item, module, asset, and presigned download URL.
3. Model `estimated_duration` carefully.
   - Prefer ISO 8601 duration strings at the API boundary.
   - Convert internally to a Python `timedelta` or a database interval-safe representation.
4. Keep ORM objects out of responses; map explicitly in services or route handlers.
5. Reserve a `DraftValidationIssue` schema now even if the validation endpoint is initially internal to Phase 2.

### Acceptance

- Route handlers can declare response envelopes with `SuccessResponse[T]` or `PaginatedResponse[T]`.
- Input validation failures surface as standard API errors.

## Workstream 4: Repository Layer

### Deliverables

- Repositories for course, module, asset, and Mongo-backed draft content.

### Steps

1. Implement `CourseRepository` methods:
   - `create`
   - `get_by_id`
   - `get_by_slug`
   - `slug_exists`
   - `update`
   - `soft_delete`
   - `list_courses`
2. Implement `ModuleRepository` methods:
   - `create`
   - `list_for_course`
   - `get_by_id`
   - `update`
   - `delete`
   - `reorder`
   - `next_sort_order`
3. Implement `AssetRepository` methods:
   - `create`
   - `list_for_module`
   - `get_by_id`
   - `update`
   - `delete`
   - `next_sort_order`
4. Implement `DraftContentRepository` on MongoDB for upserting rich content documents keyed by `course_id`.
5. Keep repository methods focused on data access; no ownership or role logic here.

### Acceptance

- Repositories are flush-based and transaction-safe.
- Queries consistently exclude soft-deleted courses.

## Workstream 5: Domain Services And Business Rules

### Deliverables

- `CourseService`, `ModuleService`, `AssetService`, `DraftValidationService`, `StorageService`, and `SlugService`.

### Steps

1. `SlugService`
   - Normalize title.
   - Generate deterministic candidates.
   - Resolve uniqueness through repository checks.
2. `CourseService`
   - Create draft courses.
   - Get detail with modules and per-module asset counts.
   - Update only allowed fields.
   - Soft-delete drafts.
   - Enforce owner-or-admin access.
   - Implement catalog listing rules for public versus instructor/admin contexts.
3. `ModuleService`
   - Create modules only for draft courses.
   - Update and delete modules only for draft courses.
   - Reorder atomically and reject invalid module IDs or duplicate lists.
4. `StorageService`
   - Upload bytes to MinIO.
   - Generate presigned URLs.
   - Delete objects when assets are removed.
   - Compute checksum and canonical storage path.
5. `AssetService`
   - Validate file type, MIME, size, and module ownership.
   - Upload to MinIO first, then persist metadata in PostgreSQL.
   - On DB failure after upload, attempt cleanup to avoid orphaned objects.
   - Restrict delete operations to draft courses.
6. `DraftValidationService`
   - Validate required metadata.
   - Require at least one module.
   - Validate module ordering and required asset policy.
   - Return structured issues that Phase 3 publishing can consume directly.

### Acceptance

- Service methods are the only place where ownership, draft-state rules, and orchestration live.
- Upload failure and cleanup paths are covered by tests.

## Workstream 6: Route Layer

### Deliverables

- Split routers for courses, modules, and assets under the existing `/api/v1/courses` prefix.

### Steps

1. Keep health endpoints in [services/course/app/api/v1/__init__.py](services/course/app/api/v1/__init__.py).
2. Add `courses.py` routes:
   - `POST /`
   - `GET /`
   - `GET /{course_id}`
   - `PATCH /{course_id}`
   - `DELETE /{course_id}`
3. Add `modules.py` routes:
   - `POST /{course_id}/modules`
   - `GET /{course_id}/modules`
   - `PATCH /{course_id}/modules/{module_id}`
   - `DELETE /{course_id}/modules/{module_id}`
   - `PATCH /{course_id}/modules/reorder`
4. Add `assets.py` routes:
   - `POST /{course_id}/modules/{module_id}/assets/upload`
   - `GET /{course_id}/modules/{module_id}/assets`
   - `GET /{course_id}/modules/{module_id}/assets/{asset_id}/download`
   - `DELETE /{course_id}/modules/{module_id}/assets/{asset_id}`
5. Use `require_roles("instructor", "admin")` on authoring routes and finer checks in services.
6. Build response `meta` consistently, following the auth-service pattern.

### Acceptance

- All Phase 2 endpoints respond through Traefik under `/api/v1/courses`.
- Routes remain thin and commit once per successful mutation.

## Workstream 7: Testing Strategy

### Deliverables

- Unit and integration coverage for core Phase 2 flows.

### Test Matrix

1. Unit tests
   - Slug generation and collision handling.
   - Draft validation rules.
   - Storage-path generation.
   - MIME and magic-byte allowlist behavior.
2. Integration tests
   - Course creation, read, update, and soft-delete.
   - Ownership and role enforcement.
   - Module create, update, delete, and reorder.
   - Asset upload, list, presigned download, and delete.
   - Public catalog stub behavior.
3. Failure-path tests
   - Upload rejects unsupported types and oversized files.
   - Reorder rejects missing or duplicate module IDs.
   - Non-owner instructor receives `403`.
   - Draft-only mutations fail once a course is not editable.

### Fixture Requirements

- DB session fixture with rollback.
- Fake or local MinIO adapter for tests.
- Fake Mongo repository or ephemeral test collection.
- Mocked current-user dependency for student, instructor, and admin roles.

### Acceptance

- Course service reaches at least 80% coverage for new logic.
- Integration tests run without external cloud dependencies.

## Workstream 8: Verification And Exit Criteria

### Manual Verification Sequence

1. Create an instructor-owned course draft.
2. Add multiple modules.
3. Reorder modules and verify persisted order.
4. Upload a supported asset and verify MinIO object creation.
5. Request a presigned download URL.
6. Delete an asset and verify MinIO cleanup.
7. Soft-delete a course and confirm it no longer appears in owner listings by default.
8. Validate a draft and confirm structured issues are returned when incomplete.

### Exit Criteria Mapping

| Phase 2 requirement | Verification |
|---------------------|-------------|
| Instructor can create course, add modules, upload assets | Integration test plus manual smoke path |
| Non-owner cannot edit | Integration test on owner and non-owner JWT contexts |
| File upload validates type and size | Unit and integration tests |
| Presigned download URL works | Integration test with storage adapter |
| Module reordering works | Integration test with persisted order assertions |
| Soft-delete works | Integration test plus repository assertions |
| MongoDB stores rich draft content | Repository test or integration check |
| Coverage target met | `pytest` coverage report for course service |

## Recommended Implementation Order

1. Models and Alembic migration.
2. Service settings and dependency providers.
3. Schemas and repository layer.
4. Slug service and course CRUD.
5. Module CRUD and reorder.
6. Storage adapter and asset flows.
7. Draft validation and catalog stub.
8. Unit and integration tests.
9. Smoke-test against the Docker stack through Traefik.

This order keeps each increment testable and limits the number of moving parts introduced at once.

## Open Questions To Resolve Early

1. Should rich draft content be stored in a single `course_drafts` document per course, or split per module for simpler partial updates?
2. Should asset download in Phase 2 allow only owners and admins, or should a student-compatible placeholder policy be added now for Phase 4 compatibility?
3. Should course creation require instructor role only, or should admins also be able to create and transfer ownership?

None of these block the initial schema and CRUD implementation, but locking them before asset and draft-content work will avoid route or schema churn.