# Phase 5 Detailed Plan — AI Assistant & Instructor Tools

## Current Repo Snapshot (Phase 5-relevant)
- `services/ai` is a skeleton service (health endpoints only) with LangChain/LangGraph, OpenAI, Qdrant, Redis, and SSE dependencies already declared.
- Search and publishing services already implement OpenAI-compatible embedding clients and Qdrant access patterns (useful references for AI retrieval/config).
- Cross-schema SQL access is already used in search service (course + publishing joins), so AI service can follow the same pattern for entitlement checks.
- AI design requirements are fully specified in `docs/AI_SYSTEM.md`, API contracts in `docs/API_CONTRACTS.md` (sections 9–10), and data models in `docs/DATA_MODELS.md` (AI jobs + Qdrant + Redis keys).

## Goals for Phase 5
1. Student Q&A with citations (non-streaming + SSE streaming).
2. Instructor enhancement tools (summary/objectives/quiz/glossary) with async job lifecycle and streaming mode.
3. Strong safety controls: entitlement checks, version gating, refusal flow, rate limiting, caching, and citation validation.
4. Analytics/event logging for AI usage.
5. Test coverage that validates RAG behavior, refusal, citation logic, and streaming.

## Key Decisions to Align Early
- **Retrieval path**: Use **direct Qdrant** retrieval in AI service (per `docs/AI_SYSTEM.md` and ai-rag instructions). Do not rely on search-service `/search/semantic` to avoid double embedding and keep AI-specific filtering logic local.
- **Entitlement verification**: Use **cross-schema SQL** reads against `course`, `publishing`, and `enrollment` schemas (similar to search service) to avoid missing endpoints in enrollment-service.
- **AI job storage**: Persist instructor jobs to **MongoDB** collection `ai_jobs` (per `docs/DATA_MODELS.md`).
- **Event logging**: Emit `AssistantQueryAsked` and `AssistantAnswerGenerated` to Kafka topic `ai.usage` (direct producer, no outbox table in AI service unless later requested).

## Implementation Plan (Detailed)

### 1) AI Service Configuration + Dependencies
- Expand `services/ai/app/config.py` to include:
  - LLM provider settings: `llm_base_url`, `llm_api_key`, `llm_model`.
  - Embeddings: `embedding_base_url`, `embedding_api_key`, `embedding_model`, `embedding_dimension`.
  - Qdrant: `qdrant_host`, `qdrant_port`, `qdrant_collection` (match publishing/search collection name).
  - Redis: cache TTLs, rate limits (student/instructor), token budgets if used.
  - Mongo: `mongo_url`, `mongo_db` for AI jobs.
  - Internal service URLs (if needed later) and `internal_service_token`.
- Update AI service lifespan to initialize:
  - Redis client (async), Qdrant client, and Mongo client.
- Add any missing dependencies for Kafka producer (e.g., `aiokafka`) if direct produce is required.
- Update `.env.example` with AI-specific variables (LLM, embeddings, qdrant, mongo, redis limits).

### 2) Shared Utilities in AI Service
Create `services/ai/app/utils/` or `services/ai/app/services/` modules:
- **LLM client wrapper** (OpenAI-compatible AsyncOpenAI):
  - Safe call wrapper with timeout/retry + error mapping to `EduCorpError` (`AI_PROVIDER_ERROR`, `AI_TIMEOUT`, etc.).
- **Embedding client**:
  - Embed question text; optionally small in-memory/Redis cache for query embeddings.
- **Qdrant retriever**:
  - Filter by `course_id` and `version_status=READY`; optional `module_id` filter.
  - `top_k=8`, `score_threshold=0.7` per `ai-rag.instructions.md`.
- **Question normalization + hashing**:
  - Lowercase + trim; hash to key for cache.
- **Rate limiter**:
  - Redis sorted-set sliding window with separate limits for student vs instructor.
- **Cache layer**:
  - Redis GET/SET for `cache:ai:{question_hash}:{course_id}:{version_id}` with TTL 3600s.

### 3) Entitlement & Ownership Checks (DB Read-Only)
Add a repository/service (SQL text queries) in AI service:
- **Enrollment check**: verify user has `ENROLLED` or `COMPLETED` status for `course_id`.
- **Course owner check**: verify `course.courses.instructor_id` matches user (unless admin).
- **READY version gating**:
  - Resolve `current_version_id` + verify `publishing.course_versions.status='READY'` and `activated_at IS NOT NULL`.
- Cache enrollment check results in Redis (`cache:enrolled:{user_id}:{course_id}` TTL 900s).

### 4) LangGraph Q&A Pipeline
Implement in `services/ai/app/services/qa_graph.py`:
- **State definition** aligned with `docs/AI_SYSTEM.md` and ai-rag instructions.
- Nodes:
  - `validate`: input schema, entitlement, rate limiting, caching pre-check.
  - `retrieve`: embedding + Qdrant search.
  - `assess`: apply thresholds; decide `generate/refuse/clarify`.
  - `generate`: LLM response with numbered chunks and system prompt.
  - `build_citations`: parse `[n]` references and validate.
  - `log_and_emit`: metrics + Kafka event payload.
- Ensure refusal and clarification paths produce structured responses.

### 5) API Schemas + Routers
Create `services/ai/app/schemas/`:
- `ai.py`:
  - `AskRequest`, `AskResponse`, `Citation`, `ClarifyRequest`, `ClarifyResponse`.
- `instructor.py`:
  - `EnhanceRequest`, `EnhanceResponse`, `JobStatusResponse`, `JobListResponse`.

Create routers:
- `services/ai/app/api/v1/ask.py`:
  - `POST /ai/ask` (non-streaming).
  - `GET /ai/ask/stream` (SSE).
  - `POST /ai/ask/clarify`.
- `services/ai/app/api/v1/instructor.py`:
  - `POST /ai/instructor/enhance`.
  - `GET /ai/instructor/enhance/stream` (SSE).
  - `GET /ai/instructor/jobs/{job_id}`.
  - `POST /ai/instructor/jobs/{job_id}/cancel`.
  - `GET /ai/instructor/jobs`.

Hook routers into `services/ai/app/api/v1/__init__.py` and keep the `/api/v1/ai` prefix.

### 6) Streaming (SSE) for Q&A
- Use `sse-starlette` `EventSourceResponse`.
- Run retrieval+assessment first; if refusal, emit `refusal` + `done`.
- Stream tokens from LLM; emit `citation` events after completion; end with `done`.
- Emit `error` event on provider failure or rate limit.

### 7) Instructor Enhancement Jobs
- **Mongo collection**: `ai_jobs` (per `docs/DATA_MODELS.md`).
- Implement repository for job CRUD in `services/ai/app/repositories/ai_jobs_repository.py`.
- Job lifecycle: `QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED`.
- Worker:
  - Use asyncio background task in AI service to process jobs (simple in-memory queue to start; optional upgrade to Celery later).
  - Retrieve relevant chunks using the same retriever (course or module scope).
  - Apply token budgeting and context truncation.
  - Use LangChain prompts from `docs/AI_SYSTEM.md`.
  - Store results + citations + tokens used.
- Streaming enhancement endpoint:
  - Use SSE; stream tokens as generated; on completion, persist job result and emit `done`.

### 8) Event Logging (AI Usage)
- Add a Kafka producer to AI service.
- Emit events to `ai.usage` for both ask + instructor tool usage.
- Include correlation ID and response type, tokens used, latency, cached flag.

### 9) Tests (Unit + Integration)
- **Unit**:
  - Citation parsing/validation.
  - Relevance assessment routing.
  - Rate limiter behavior (allow/deny).
  - Cache hit vs miss logic.
- **Integration**:
  - `POST /ai/ask` happy path with mocked LLM via `respx`.
  - Refusal path (insufficient chunks).
  - Streaming endpoint emits `token`, `citation`, `done`.
  - Instructor job lifecycle: create → complete → cancel.
- Use test fixtures from `services/ai/tests/conftest.py` and follow `docs/TESTING_STRATEGY.md`.

### 10) Frontend (Phase 5 UX)
Add minimal UI to `apps/web`:
- Student AI assistant panel (per-course): route or component under `/app/courses/:courseId`.
- Instructor enhancements: module/course enhancement UI with job status list and results.
- SSE streaming handling with optimistic UI for live tokens.
- Error states using the standard API envelope.

## Critical Files to Modify / Add
- `services/ai/app/config.py`
- `services/ai/app/main.py` (lifespan setup for Redis/Mongo/Qdrant)
- `services/ai/app/dependencies.py` (Redis/Mongo/Qdrant providers)
- `services/ai/app/api/v1/__init__.py`
- `services/ai/app/api/v1/ask.py`
- `services/ai/app/api/v1/instructor.py`
- `services/ai/app/schemas/ai.py`
- `services/ai/app/schemas/instructor.py`
- `services/ai/app/services/qa_graph.py`
- `services/ai/app/services/llm_client.py`
- `services/ai/app/services/retriever.py`
- `services/ai/app/services/rate_limiter.py`
- `services/ai/app/repositories/ai_jobs_repository.py`
- `services/ai/app/repositories/entitlement_repository.py`
- `services/ai/tests/unit/*`
- `services/ai/tests/integration/*`
- `apps/web/src/features/ai/*` (new)
- `.env.example` (AI env vars)

## Verification Checklist
- **Backend**:
  - `POST /api/v1/ai/ask` returns answer with citations for enrolled student.
  - `GET /api/v1/ai/ask/stream` emits SSE token/citation/done events.
  - Refusal when context insufficient or user not enrolled.
  - Instructor enhancement job lifecycle works via `POST /ai/instructor/enhance` and `GET /ai/instructor/jobs/{job_id}`.
  - Rate limiting returns 429 with error envelope.
- **Tests**:
  - `pytest services/ai/tests/ -v --tb=short` passes.
- **Frontend**:
  - Student can ask questions and see streaming answers.
  - Instructor can run summary/quiz job and see results.

---
This plan is ready to be converted into the Phase 5 implementation checklist and added to the repo as `docs/phase 5.md` (or the path you prefer).
# Phase 5 Detailed Plan — AI Assistant & Instructor Tools

## Current Repo Snapshot (Phase 5-relevant)
- `services/ai` is a skeleton service (health endpoints only) with LangChain/LangGraph, OpenAI, Qdrant, Redis, and SSE dependencies already declared.
- Search and publishing services already implement OpenAI-compatible embedding clients and Qdrant access patterns (useful references for AI retrieval/config).
- Cross-schema SQL access is already used in search service (course + publishing joins), so AI service can follow the same pattern for entitlement checks.
- AI design requirements are fully specified in `docs/AI_SYSTEM.md`, API contracts in `docs/API_CONTRACTS.md` (sections 9–10), and data models in `docs/DATA_MODELS.md` (AI jobs + Qdrant + Redis keys).

## Goals for Phase 5
1. Student Q&A with citations (non-streaming + SSE streaming).
2. Instructor enhancement tools (summary/objectives/quiz/glossary) with async job lifecycle and streaming mode.
3. Strong safety controls: entitlement checks, version gating, refusal flow, rate limiting, caching, and citation validation.
4. Analytics/event logging for AI usage.
5. Test coverage that validates RAG behavior, refusal, citation logic, and streaming.

## Key Decisions to Align Early
- **Retrieval path**: Use **direct Qdrant** retrieval in AI service (per `docs/AI_SYSTEM.md` and ai-rag instructions). Do not rely on search-service `/search/semantic` to avoid double embedding and keep AI-specific filtering logic local.
- **Entitlement verification**: Use **cross-schema SQL** reads against `course`, `publishing`, and `enrollment` schemas (similar to search service) to avoid missing endpoints in enrollment-service.
- **AI job storage**: Persist instructor jobs to **MongoDB** collection `ai_jobs` (per `docs/DATA_MODELS.md`).
- **Event logging**: Emit `AssistantQueryAsked` and `AssistantAnswerGenerated` to Kafka topic `ai.usage` (direct producer, no outbox table in AI service unless later requested).

## Implementation Plan (Detailed)

### 1) AI Service Configuration + Dependencies
- Expand `services/ai/app/config.py` to include:
  - LLM provider settings: `llm_base_url`, `llm_api_key`, `llm_model`.
  - Embeddings: `embedding_base_url`, `embedding_api_key`, `embedding_model`, `embedding_dimension`.
  - Qdrant: `qdrant_host`, `qdrant_port`, `qdrant_collection` (match publishing/search collection name).
  - Redis: cache TTLs, rate limits (student/instructor), token budgets if used.
  - Mongo: `mongo_url`, `mongo_db` for AI jobs.
  - Internal service URLs (if needed later) and `internal_service_token`.
- Update AI service lifespan to initialize:
  - Redis client (async), Qdrant client, and Mongo client.
- Add any missing dependencies for Kafka producer (e.g., `aiokafka`) if direct produce is required.
- Update `.env.example` with AI-specific variables (LLM, embeddings, qdrant, mongo, redis limits).

### 2) Shared Utilities in AI Service
Create `services/ai/app/utils/` or `services/ai/app/services/` modules:
- **LLM client wrapper** (OpenAI-compatible AsyncOpenAI):
  - Safe call wrapper with timeout/retry + error mapping to `EduCorpError` (`AI_PROVIDER_ERROR`, `AI_TIMEOUT`, etc.).
- **Embedding client**:
  - Embed question text; optionally small in-memory/Redis cache for query embeddings.
- **Qdrant retriever**:
  - Filter by `course_id` and `version_status=READY`; optional `module_id` filter.
  - `top_k=8`, `score_threshold=0.7` per `ai-rag.instructions.md`.
- **Question normalization + hashing**:
  - Lowercase + trim; hash to key for cache.
- **Rate limiter**:
  - Redis sorted-set sliding window with separate limits for student vs instructor.
- **Cache layer**:
  - Redis GET/SET for `cache:ai:{question_hash}:{course_id}:{version_id}` with TTL 3600s.

### 3) Entitlement & Ownership Checks (DB Read-Only)
Add a repository/service (SQL text queries) in AI service:
- **Enrollment check**: verify user has `ENROLLED` or `COMPLETED` status for `course_id`.
- **Course owner check**: verify `course.courses.instructor_id` matches user (unless admin).
- **READY version gating**:
  - Resolve `current_version_id` + verify `publishing.course_versions.status='READY'` and `activated_at IS NOT NULL`.
- Cache enrollment check results in Redis (`cache:enrolled:{user_id}:{course_id}` TTL 900s).

### 4) LangGraph Q&A Pipeline
Implement in `services/ai/app/services/qa_graph.py`:
- **State definition** aligned with `docs/AI_SYSTEM.md` and ai-rag instructions.
- Nodes:
  - `validate`: input schema, entitlement, rate limiting, caching pre-check.
  - `retrieve`: embedding + Qdrant search.
  - `assess`: apply thresholds; decide `generate/refuse/clarify`.
  - `generate`: LLM response with numbered chunks and system prompt.
  - `build_citations`: parse `[n]` references and validate.
  - `log_and_emit`: metrics + Kafka event payload.
- Ensure refusal and clarification paths produce structured responses.

### 5) API Schemas + Routers
Create `services/ai/app/schemas/`:
- `ai.py`:
  - `AskRequest`, `AskResponse`, `Citation`, `ClarifyRequest`, `ClarifyResponse`.
- `instructor.py`:
  - `EnhanceRequest`, `EnhanceResponse`, `JobStatusResponse`, `JobListResponse`.

Create routers:
- `services/ai/app/api/v1/ask.py`:
  - `POST /ai/ask` (non-streaming).
  - `GET /ai/ask/stream` (SSE).
  - `POST /ai/ask/clarify`.
- `services/ai/app/api/v1/instructor.py`:
  - `POST /ai/instructor/enhance`.
  - `GET /ai/instructor/enhance/stream` (SSE).
  - `GET /ai/instructor/jobs/{job_id}`.
  - `POST /ai/instructor/jobs/{job_id}/cancel`.
  - `GET /ai/instructor/jobs`.

Hook routers into `services/ai/app/api/v1/__init__.py` and keep the `/api/v1/ai` prefix.

### 6) Streaming (SSE) for Q&A
- Use `sse-starlette` `EventSourceResponse`.
- Run retrieval+assessment first; if refusal, emit `refusal` + `done`.
- Stream tokens from LLM; emit `citation` events after completion; end with `done`.
- Emit `error` event on provider failure or rate limit.

### 7) Instructor Enhancement Jobs
- **Mongo collection**: `ai_jobs` (per `docs/DATA_MODELS.md`).
- Implement repository for job CRUD in `services/ai/app/repositories/ai_jobs_repository.py`.
- Job lifecycle: `QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED`.
- Worker:
  - Use asyncio background task in AI service to process jobs (simple in-memory queue to start; optional upgrade to Celery later).
  - Retrieve relevant chunks using the same retriever (course or module scope).
  - Apply token budgeting and context truncation.
  - Use LangChain prompts from `docs/AI_SYSTEM.md`.
  - Store results + citations + tokens used.
- Streaming enhancement endpoint:
  - Use SSE; stream tokens as generated; on completion, persist job result and emit `done`.

### 8) Event Logging (AI Usage)
- Add a Kafka producer to AI service.
- Emit events to `ai.usage` for both ask + instructor tool usage.
- Include correlation ID and response type, tokens used, latency, cached flag.

### 9) Tests (Unit + Integration)
- **Unit**:
  - Citation parsing/validation.
  - Relevance assessment routing.
  - Rate limiter behavior (allow/deny).
  - Cache hit vs miss logic.
- **Integration**:
  - `POST /ai/ask` happy path with mocked LLM via `respx`.
  - Refusal path (insufficient chunks).
  - Streaming endpoint emits `token`, `citation`, `done`.
  - Instructor job lifecycle: create → complete → cancel.
- Use test fixtures from `services/ai/tests/conftest.py` and follow `docs/TESTING_STRATEGY.md`.

### 10) Frontend (Phase 5 UX)
Add minimal UI to `apps/web`:
- Student AI assistant panel (per-course): route or component under `/app/courses/:courseId`.
- Instructor enhancements: module/course enhancement UI with job status list and results.
- SSE streaming handling with optimistic UI for live tokens.
- Error states using the standard API envelope.

## Critical Files to Modify / Add
- `services/ai/app/config.py`
- `services/ai/app/main.py` (lifespan setup for Redis/Mongo/Qdrant)
- `services/ai/app/dependencies.py` (Redis/Mongo/Qdrant providers)
- `services/ai/app/api/v1/__init__.py`
- `services/ai/app/api/v1/ask.py`
- `services/ai/app/api/v1/instructor.py`
- `services/ai/app/schemas/ai.py`
- `services/ai/app/schemas/instructor.py`
- `services/ai/app/services/qa_graph.py`
- `services/ai/app/services/llm_client.py`
- `services/ai/app/services/retriever.py`
- `services/ai/app/services/rate_limiter.py`
- `services/ai/app/repositories/ai_jobs_repository.py`
- `services/ai/app/repositories/entitlement_repository.py`
- `services/ai/tests/unit/*`
- `services/ai/tests/integration/*`
- `apps/web/src/features/ai/*` (new)
- `.env.example` (AI env vars)

## Verification Checklist
- **Backend**:
  - `POST /api/v1/ai/ask` returns answer with citations for enrolled student.
  - `GET /api/v1/ai/ask/stream` emits SSE token/citation/done events.
  - Refusal when context insufficient or user not enrolled.
  - Instructor enhancement job lifecycle works via `POST /ai/instructor/enhance` and `GET /ai/instructor/jobs/{job_id}`.
  - Rate limiting returns 429 with error envelope.
- **Tests**:
  - `pytest services/ai/tests/ -v --tb=short` passes.
- **Frontend**:
  - Student can ask questions and see streaming answers.
  - Instructor can run summary/quiz job and see results.

---
This plan is ready to be converted into the Phase 5 implementation checklist and added to the repo as `docs/phase 5.md` (or the path you prefer).
