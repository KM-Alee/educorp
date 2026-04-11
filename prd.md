# PRD — EduCorp: Intelligent Course Delivery Platform (Backend + Product Requirements)

**Document status:** Final PRD (v1.0)  
**Product:** EduCorp — Intelligent Course Delivery Platform  
**Audience:** Engineering, Product, Design, QA, Data, Ops/SRE  
**Primary users:** Students, Instructors, Admins  
**Core value proposition:** Enable instructors to publish asset-rich courses that are automatically processed for search + AI assistance, and enable students to enroll, learn, track progress, and ask contextual questions answered strictly from course material with citations.

---

## 1) Problem Statement

### 1.1 What problem are we solving?
Current course platforms commonly suffer from:
- Content is hard to search and harder to learn from (PDFs/videos not “AI-ready”).
- Publishing changes are risky: partial processing leads to broken course states.
- Enrollment and progress tracking can be inconsistent under high load.
- Learners can’t easily ask “course-specific” questions with trustworthy citations.
- Instructors spend time manually creating objectives, quizzes, and summaries.

### 1.2 Target outcomes
- Reliable course publishing pipeline that never exposes partially processed content.
- Scalable enrollment + progress tracking with strict correctness for core records.
- AI assistant that answers using only the course’s published material, with citations.
- Actionable analytics for course performance and platform usage.

---

## 2) Goals, Non-Goals, and Assumptions

### 2.1 Goals (Must achieve)
1. **Correctness for core transactions**
   - Enrollments must not duplicate.
   - Course publishing must not corrupt the live course.
   - Progress and completion must be correct and auditable.
2. **Safe publishing & versioning**
   - Students only see course versions marked **READY**.
   - Previous READY version remains live while new version processes.
3. **AI-powered learning**
   - Contextual Q&A per course version, with citations.
   - Instructor content enhancement (summaries, objectives, quizzes).
4. **Observability & traceability**
   - Every key workflow is traceable end-to-end (correlation IDs, audit logs).
   - Failures are visible and actionable.

### 2.2 Non-Goals (Out of scope for v1)
- Real-time collaborative editing for instructors.
- Payments/subscriptions.
- Full LMS features (grading, assignments, proctored exams).
- External internet browsing by the assistant (assistant is course-scoped).
- Mobile offline mode (can be later).

### 2.3 Assumptions
- Courses consist of structured modules plus uploaded assets (documents, slides, video transcripts, etc.).
- AI responses are best-effort but must be constrained to retrieved content.
- “Strong consistency” applies to **systems of record** (core Postgres-backed transactional data). Derived indexes (search/vector/analytics) may be eventually consistent, but must never violate gating rules (e.g., only READY content is served).

---

## 3) Personas & Permissions

### 3.1 Personas
- **Student:** browses catalog, enrolls, learns, tracks progress, asks AI questions.
- **Instructor:** creates and manages courses, uploads assets, publishes versions, requests AI enhancements, views course analytics.
- **Admin:** manages users/roles, moderates courses, views platform analytics, handles escalations.
- **Support/Ops (internal):** investigates workflow failures, retries jobs, monitors system health.
- **Data Analyst (internal):** accesses aggregated usage and performance metrics.

### 3.2 Roles & permissions (RBAC)
- **Student:** read course catalog; enroll; access enrolled course content; AI Q&A for enrolled courses; view own progress/certificates.
- **Instructor:** create/edit drafts; upload assets; publish; view instructor analytics; use AI enhancement for own courses.
- **Admin:** all instructor capabilities + manage users/roles + manage course visibility + platform analytics.
- Access to course content and AI retrieval must be enforced by **entitlement checks** (enrolled OR public preview rules as defined).

---

## 4) Scope Overview (Epics)

1. Authentication & User Management  
2. Course Authoring & Draft Management  
3. Asset Ingestion & Publishing Workflow (versioned)  
4. Course Catalog, Search & Retrieval  
5. Enrollment (with prerequisites/capacity)  
6. Progress Tracking, Completion & Certificates  
7. AI Assistant (student Q&A)  
8. AI Instructor Tools (enhancement jobs)  
9. Notifications  
10. Analytics & Reporting  
11. Observability, Audit, Admin Ops Tools  

---

## 5) Functional Requirements (Detailed)

### Epic 1 — Authentication & User Management
**FR1.1 Registration & login**
- Users can register and login via email/password or SSO (SSO optional for v1).
- JWT access tokens + refresh tokens supported.
- Password resets and account verification (email).

**FR1.2 RBAC**
- Roles: student, instructor, admin.
- Admin can change roles.
- Instructor activation may require admin approval (configurable).

**FR1.3 User events**
- Emit events for user lifecycle (created, role changed) for analytics and downstream systems.

**Acceptance criteria**
- Token validation works across all APIs.
- Role-protected endpoints reject unauthorized requests.
- All auth-related actions are auditable (timestamp, actor, target).

---

### Epic 2 — Course Authoring & Draft Management
**FR2.1 Course structure**
- Instructor can create a course draft with:
  - Title, description, category/tags, difficulty, estimated duration
  - Modules (ordered)
  - Assets per module (ordered)
- Course draft is editable until published.

**FR2.2 Draft validation**
- Pre-publish validation:
  - Required metadata present
  - At least one module
  - Asset formats allowed
  - Optional: minimum content threshold

**FR2.3 Course visibility**
- Course visibility states:
  - Draft (instructor-only)
  - Published processing (not visible to students)
  - READY (visible to eligible students)
  - FAILED (visible to instructor/admin with error details)

**Acceptance criteria**
- Instructors can create/edit drafts without affecting the currently live version.
- Validation errors are returned as structured messages.

---

### Epic 3 — Asset Ingestion & Publishing Workflow (Versioned)
**FR3.1 Course versioning**
- Publishing creates a new immutable **course_version** record.
- A course may have:
  - One current READY version
  - One in-progress version (PUBLISHING)
  - Historical versions (READY/FAILED)

**FR3.2 Publishing workflow steps**
When an instructor publishes:
1. Persist version metadata and set status **PUBLISHING**.
2. Trigger durable workflow processing:
   - Extract text from assets (PDF/doc/transcripts/etc.)
   - Normalize text (cleaning, language detection optional)
   - Chunk content with metadata (module, asset source, offsets)
   - Generate embeddings
   - Index for keyword search (optional but recommended)
3. On success: mark version **READY**
4. On failure: mark **PUBLISH_FAILED** with diagnostic details and retry options.

**FR3.3 Safety guarantees (product-level)**
- Students may only query/browse/AI-retrieve from versions in **READY** state.
- If publishing a new version fails, the old READY version remains live and unaffected.
- Instructor can re-run publishing after fixing assets/settings.

**FR3.4 Admin/ops controls**
- View workflow status, step-level failures, and retry from last safe checkpoint.
- Cancel in-progress publishing if needed.

**Acceptance criteria**
- No partially processed version is visible to students.
- Workflow failures are surfaced with actionable diagnostics.
- Re-publishing does not create duplicate visible content.

---

### Epic 4 — Course Catalog, Search & Retrieval
**FR4.1 Browse catalog**
- List courses with filters: category, tag, difficulty, instructor, popularity, newest.
- Only show READY versions (and only courses visible to that user).

**FR4.2 Keyword search**
- Search by title/description and optionally indexed content.
- Results return course + matched module/asset references when available.

**FR4.3 Semantic retrieval (for AI + optionally search)**
- Retrieve top-k relevant chunks for a query scoped to:
  - course_id
  - course_version=READY (or specified READY version)
  - user entitlement
- Return chunk text + metadata for citations.

**Acceptance criteria**
- Search results never reference non-READY content for students.
- Retrieval is reliably scoped and permission-checked.

---

### Epic 5 — Enrollment
**FR5.1 Enroll**
- Student enrolls in a course (course_id).
- Enrollment must be idempotent:
  - Repeat requests return the existing enrollment result.
  - Duplicate enrollments are prevented (unique rule).

**FR5.2 Prerequisites**
- Course may require prerequisite course(s) completion.
- Enrollment request is rejected if prerequisites not met.

**FR5.3 Capacity**
- Course may define capacity.
- Enrollment must not exceed capacity under concurrency.
- When full, enrollment rejects with “course full” and current availability.

**FR5.4 Enrollment lifecycle**
- States: ENROLLED, CANCELLED (optional), COMPLETED (derived from progress).
- Enrollment history/audit trail retained.

**Acceptance criteria**
- Under high concurrency, capacity and duplicate rules are enforced correctly.
- Enrollment response returns immediately with enrollment_id and state.

---

### Epic 6 — Progress Tracking, Completion & Certificates
**FR6.1 Progress initialization**
- When enrollment succeeds, initialize student progress per module/item:
  - module completion flags
  - timestamps
  - progress percentage
- Must be safe under retries (no duplicates).

**FR6.2 Progress updates**
- Student can mark lessons complete (or system auto-tracks via events if applicable).
- Update progress percentage and completion state.

**FR6.3 Completion**
- Course completion occurs when all required modules are complete.
- On completion:
  - Emit completion event
  - Generate certificate record (PDF generation optional for v1; at minimum store certificate data)

**FR6.4 Student views**
- Student can see progress dashboard, completion history, certificates.

**Acceptance criteria**
- Completion is computed consistently and is auditable.
- Certificates are issued exactly once per completed enrollment.

---

### Epic 7 — AI Assistant (Student Contextual Q&A)
**FR7.1 Ask a question**
- Student asks: `{course_id, question}` (optionally module scope).
- System verifies user entitlement to course content.

**FR7.2 Retrieval-augmented generation**
- Retrieve top-k course chunks from the READY version.
- Build an answer with:
  - concise response
  - citations referencing chunk IDs and source metadata (module/asset)
  - refusal behavior if insufficient context (“Not enough information in course materials.”)

**FR7.3 Streaming**
- Support streaming response (SSE or WebSocket).
- Provide partial tokens and final structured payload including citations.

**FR7.4 Clarification**
- If question is ambiguous, assistant asks clarifying question instead of hallucinating.

**FR7.5 Safety + quality**
- Must not leak content from other courses or unpublished versions.
- Must not fabricate citations (citations must map to retrieved chunks).

**Acceptance criteria**
- Responses contain citations for material claims.
- If retrieval returns low confidence/empty, assistant refuses or asks for clarification.
- Latency meets targets (see NFRs).

---

### Epic 8 — AI Instructor Tools (Content Enhancement)
**FR8.1 Enhancement requests**
Instructor can request:
- Summaries (module/course)
- Learning objectives
- Quiz questions (MCQ/short answer) with answer keys
- Glossary/flashcards (optional)

**FR8.2 Delivery modes**
- Streaming response for interactive usage
- Async jobs:
  - Create job → returns job_id
  - Poll job status → returns result when ready
  - Job can be cancelled

**FR8.3 Provenance**
- Outputs link back to the course/version used and retrieved citations where applicable.

**Acceptance criteria**
- Job lifecycle is visible (queued/running/succeeded/failed).
- Failures provide an error code and retry guidance.

---

### Epic 9 — Notifications
**FR9.1 Notification triggers**
- Enrollment confirmation
- Course published/ready (to instructor)
- Course completion/certificate available
- Admin actions (role changes, moderation actions)

**FR9.2 Channels**
- Email (v1)
- In-app notifications (v1 recommended)
- Push (optional later)

**FR9.3 Reliability**
- Notifications are best-effort and must not block core user actions.
- Retries with backoff; failures are tracked.

**Acceptance criteria**
- Notification delivery is decoupled from enrollment/publishing latency.
- Users can view notification history (in-app) if enabled.

---

### Epic 10 — Analytics & Reporting
**FR10.1 Platform analytics**
Track and report:
- Total students/instructors
- Enrollments over time (day/week/month)
- Completion rate
- Time-to-complete distribution
- Popular courses
- AI usage: asked/answered/failed, latency, refusal rate

**FR10.2 Instructor analytics**
Per course:
- enrollments, active learners, completion rate
- top searched topics (optional)
- AI assistant usage in that course

**FR10.3 Data quality**
- Analytics must be derived from immutable events where possible.
- Backfills supported (replay from event logs) for recovery.

**Acceptance criteria**
- Dashboards match event counts with tolerable lag (see NFR).
- Metrics definitions documented and consistent.

---

### Epic 11 — Observability, Audit, Admin Ops
**FR11.1 Correlation & tracing**
- Every request/workflow/event has:
  - correlation_id
  - actor/user_id (where applicable)
  - entity IDs (course_id, enrollment_id, version_id)

**FR11.2 Audit logs**
- Persist audit records for:
  - role changes
  - publish actions
  - enrollment actions (and rejects, optionally)
  - admin overrides

**FR11.3 Ops console (minimum)**
- View workflow health, failures, retries, DLQ counts, consumer lag.
- Ability to replay/retry failed processing safely.

**Acceptance criteria**
- Support/Ops can identify why a course failed to publish within minutes.
- Key workflows can be traced end-to-end.

---

## 6) Data Objects (Conceptual Model)

### Core entities
- **User**: id, email, roles, status, created_at
- **Course**: id, owner_instructor_id, metadata fields, visibility flags
- **Module**: id, course_id, order, title
- **Asset**: id, module_id, type, location, upload metadata
- **CourseVersion**: id, course_id, version_number, status (PUBLISHING/READY/FAILED), created_at, ready_at
- **Enrollment**: id, course_id, student_id, state, created_at
- **Progress**: enrollment_id, module_id, completion_state, progress_percent, timestamps
- **Certificate**: enrollment_id, issued_at, certificate_payload

### AI/retrieval entities (derived)
- **Chunk**: chunk_id, course_id, version_id, module_id, asset_id, text, offsets, metadata
- **Embedding**: chunk_id, vector, embedding_model_version, created_at

### Events (examples)
- CoursePublishRequested, CourseReady, CoursePublishFailed  
- EnrollmentCreated, ProgressInitialized, CourseCompleted  
- AssistantQueryAsked, AssistantAnswerGenerated, AssistantFailed  
- NotificationRequested

---

## 7) Non-Functional Requirements (NFRs)

### 7.1 Consistency & correctness
- **Core transactional correctness (must):**
  - Enrollment uniqueness and capacity correctness.
  - Course version state transitions are atomic and auditable.
- **Derived systems (allowed eventual consistency):**
  - Search indexes, vector indexes, analytics projections may lag, but must be gated so students only access READY material.

### 7.2 Performance targets
- Catalog browse p95 latency: **< 300ms**
- Enrollment command p95 latency: **< 500ms**
- AI assistant time-to-first-token (streaming) p95: **< 2s** (excluding provider outages)
- AI assistant full response p95: **< 20s** for typical prompts
- Publish processing:
  - Small course (<50 pages equivalent): **< 5 minutes**
  - Medium course: **< 30 minutes** (configurable; depends on assets)

### 7.3 Availability & resilience
- Core APIs (auth, course, enrollment, progress): **99.9%** target
- Publishing and analytics pipelines: **eventually completes**, must surface backlog/lag
- Graceful degradation:
  - If AI provider fails, platform learning still works; show error and log event.

### 7.4 Security & privacy
- Encrypt sensitive data at rest and in transit.
- Secrets management (LLM keys, JWT signing keys).
- PII minimization in logs/traces.
- Access control enforced at all entry points (gateway + services).
- Rate limiting for AI endpoints to prevent abuse/cost spikes.

### 7.5 Compliance & retention
- Data retention policies:
  - Audit logs retained (e.g., 1–3 years configurable)
  - AI prompts/responses retention configurable; default minimal retention
- Right-to-delete support (user deletion impact on analytics/events defined).

### 7.6 Observability SLOs
- Structured logs with correlation IDs.
- Metrics: error rates, latency, workflow failures, consumer lag, queue depth.
- Alerting for:
  - publish failure spikes
  - enrollment failure spikes
  - AI provider failure spikes
  - Kafka consumer lag thresholds
  - workflow backlog thresholds

---

## 8) Key User Journeys (E2E)

### Journey A — Instructor publishes a course
1. Instructor edits draft and uploads assets.
2. Instructor hits Publish.
3. New course version enters PUBLISHING.
4. Processing runs (extract → chunk → embed → index).
5. On success, status becomes READY; course becomes visible/searchable.
6. On failure, instructor sees failure reason and retry guidance; old READY version remains live.

### Journey B — Student enrolls and starts learning
1. Student browses READY courses.
2. Student enrolls (idempotent).
3. Progress records initialized.
4. Student completes modules; progress updates.
5. When all required modules complete, course marked completed; certificate issued.

### Journey C — Student asks AI assistant
1. Student asks a question within an enrolled course.
2. System retrieves relevant chunks from READY version.
3. Assistant streams response with citations.
4. Usage logged to analytics.

---

## 9) Success Metrics (KPIs)

### Adoption & engagement
- Weekly active learners
- Enrollment conversion rate (browse → enroll)
- Course completion rate
- Median time-to-complete by course

### AI effectiveness
- AI usage per active learner
- Answer success rate (answered vs failed)
- Refusal rate (should be meaningful, not near-zero)
- Citation coverage (answers containing valid citations)
- User feedback score on AI answers (thumbs up/down optional)

### Reliability & ops
- Publish success rate
- Median publish processing duration by course size
- Enrollment error rate
- Consumer lag and DLQ rates
- Incident rate attributable to workflow failures

---

## 10) Acceptance Criteria Summary (Release-level)

A release is acceptable when:
- Students can enroll without duplicates; capacity is enforced correctly under concurrency.
- Only READY course versions are visible/searchable and usable by AI.
- Publishing failures do not corrupt live course availability.
- AI assistant returns cited answers and refuses when lacking evidence.
- Observability exists to debug failures (trace IDs, workflow IDs, event IDs).
- Notifications and analytics operate asynchronously without blocking core flows.

---

---

## 11) Technology Stack & Architecture Decisions

### 11.1 Core Backend
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API Framework | **FastAPI** (Python 3.12+) | Async-first, automatic OpenAPI docs, Pydantic validation |
| Authentication | **JWT** (access + refresh tokens) | Stateless, scalable, standard |
| Task Queue | **Celery** + **RabbitMQ** | Reliable background jobs (emails, notifications) |

### 11.2 Event Streaming & Messaging
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Event Bus | **Apache Kafka** + **ZooKeeper** | Durable event log, replay capability, high throughput |
| Schema Enforcement | **Confluent Schema Registry** (Avro/JSON Schema) | Prevent breaking changes in event contracts |
| Task Queues | **RabbitMQ** | Celery broker for best-effort jobs (notifications) |

### 11.3 Workflow Orchestration
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Durable Workflows | **Temporal** | Publishing pipeline, enrollment sagas; built-in retry, visibility, versioning |

### 11.4 Data Stores
| Store | Technology | Purpose |
|-------|-----------|---------|
| System of Record | **PostgreSQL 16** | Users, enrollments, progress, versions, audit (ACID) |
| Content Store | **MongoDB** | Flexible course content, draft JSON, asset metadata |
| Cache / Rate Limiter | **Redis** | Caching, idempotency keys, rate limiting, session store |
| Vector Store | **Qdrant** | Embeddings + semantic search (primary) |
| Vector (fallback) | **pgvector** | Simpler vector search inside Postgres if Qdrant unavailable |
| Object Storage | **MinIO** (dev) / **S3-compatible** (prod) | Asset file storage (PDFs, DOCX, media) |

### 11.5 AI / LLM Stack
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | **LangChain** + **LangGraph** | RAG pipelines, agent workflows, tool orchestration |
| LLM Provider | **NanoGPT** (OpenAI-compatible API) | Chat completions, content generation |
| Embeddings | **OpenAI-compatible embeddings API** | Text-to-vector for semantic search |

### 11.6 Communication & Realtime
| Channel | Technology | Purpose |
|---------|-----------|---------|
| Streaming AI | **Server-Sent Events (SSE)** | AI assistant streaming responses |
| Realtime (optional) | **WebSocket** | Live notifications, progress updates |

### 11.7 Observability & Monitoring
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Instrumentation | **OpenTelemetry** | Distributed tracing, metrics, structured logs |
| Metrics | **Prometheus** | Time-series metrics collection |
| Visualization | **Grafana** | Dashboards, alerting |
| Tracing | **Jaeger** | Distributed request tracing |

### 11.8 DevOps & Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containerization | **Docker** | Service packaging |
| Orchestration (dev) | **Docker Compose** | Local multi-service development |
| Reverse Proxy | **Traefik** or **Nginx** | API gateway, TLS termination, routing |

### 11.9 Architecture Patterns
- **Service-Oriented Architecture** with clear domain boundaries (auth, course, enrollment, progress, AI, search, notification, analytics)
- **Transactional Outbox Pattern** — reliable event publishing from PostgreSQL to Kafka
- **Idempotency Keys** — all write APIs accept idempotency keys for safe retries
- **RAG (Retrieval-Augmented Generation)** — course-scoped, version-gated semantic retrieval
- **Event-Driven Architecture** — Kafka as the event backbone for analytics, notifications, and cross-service communication
- **CQRS-lite** — separate read models (search indexes, analytics projections) from write models (PostgreSQL)

---

## 12) Risks & Mitigations

1. **Consistency confusion across stores**
   - Mitigation: explicit READY gating, clear “system-of-record vs derived” rules, strong DB constraints.
2. **Operational complexity (multiple brokers/workflow engines)**
   - Mitigation: limit primitives; define strict usage rules; invest in observability and runbooks.
3. **AI hallucinations / low trust**
   - Mitigation: citation enforcement, refusal behavior, user feedback loop, evaluation set.
4. **Cost blowups from AI usage**
   - Mitigation: rate limits, caching, token budgets, model tiers, quotas per org/user.
5. **Capacity/prerequisite race conditions**
   - Mitigation: transactional enforcement and concurrency-safe capacity checks.

---

## 13) Resolved Design Decisions (formerly Open Questions)

| # | Question | Decision (v1) | Rationale |
|---|----------|---------------|-----------|
| 1 | Are courses public, private, or both? | **Both.** Courses default to private (enrolled-only). Instructors can mark courses as "public preview" which shows metadata + first module free. Full content requires enrollment. | Balances discoverability with content protection. |
| 2 | Admin approval for instructor activation? | **Yes, configurable.** Default: admin approval required. Env flag `INSTRUCTOR_AUTO_APPROVE=false` to toggle. | Prevents spam courses while allowing flexibility. |
| 3 | Certificate format? | **Record-only for v1.** Store certificate data (enrollment_id, completion_date, course_title, student_name, unique cert ID). PDF generation deferred to v2. | Reduces scope; record is sufficient for verification. |
| 4 | Asset types supported in v1? | **PDF, DOCX, PPTX, plain text (.txt, .md), video transcript (.vtt, .srt).** | Covers 90% of educational content. Video/audio files stored but not transcribed in v1. |
| 5 | AI prompt/response retention? | **Store for 90 days** (configurable via `AI_RETENTION_DAYS`). Anonymize after retention period. Used for quality evaluation and abuse detection. | Balances privacy with operational needs. |
| 6 | Analytics granularity? | **Per-course and per-module for v1.** Per-asset and per-session analytics deferred. | Keeps analytics pipeline manageable. |

---

## 14) Glossary

| Term | Definition |
|------|-----------|
| **Course Version** | An immutable snapshot of course content created on publish. Only READY versions are visible to students. |
| **Chunk** | A segment of extracted text from a course asset, enriched with metadata (module, asset, offsets). Used for search and RAG. |
| **READY** | The state of a course version that has completed all processing and is safe to serve to students. |
| **Transactional Outbox** | A pattern where events are written to a database table in the same transaction as the business operation, then asynchronously relayed to Kafka. |
| **Idempotency Key** | A client-provided unique key that ensures a write operation produces the same result regardless of how many times it is retried. |
| **RAG** | Retrieval-Augmented Generation — fetching relevant document chunks before generating an AI response, grounding the answer in source material. |
| **Entitlement** | The access right a user has to course content, derived from enrollment status. |
| **DLQ** | Dead Letter Queue — where failed messages are sent after exhausting retries, for manual inspection. |
| **Correlation ID** | A unique identifier propagated across all services and logs for a single user request or workflow execution. |