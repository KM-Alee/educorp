# EduCorp — Data Models

## 1. PostgreSQL Schemas

All tables use UUIDs as primary keys, `created_at`/`updated_at` timestamps, and soft-delete where appropriate. Each service owns its schema namespace.

---

### 1.1 Auth Schema (`auth`)

```sql
-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE auth.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url      VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ  -- soft delete
);

CREATE INDEX idx_users_email ON auth.users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_active ON auth.users(is_active) WHERE deleted_at IS NULL;

-- ============================================================
-- ROLES
-- ============================================================
CREATE TABLE auth.roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) NOT NULL UNIQUE,  -- 'student', 'instructor', 'admin'
    description VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- USER_ROLES (many-to-many)
-- ============================================================
CREATE TABLE auth.user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES auth.roles(id) ON DELETE CASCADE,
    granted_by  UUID REFERENCES auth.users(id),
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON auth.user_roles(user_id);

-- ============================================================
-- REFRESH TOKENS
-- ============================================================
CREATE TABLE auth.refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    device_info     VARCHAR(255),
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user ON auth.refresh_tokens(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_tokens_expiry ON auth.refresh_tokens(expires_at);

-- ============================================================
-- PASSWORD RESETS
-- ============================================================
CREATE TABLE auth.password_resets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- EMAIL VERIFICATION TOKENS
-- ============================================================
CREATE TABLE auth.email_verifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- INSTRUCTOR APPLICATIONS (admin approval flow)
-- ============================================================
CREATE TABLE auth.instructor_applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    reason          TEXT,
    reviewed_by     UUID REFERENCES auth.users(id),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 1.2 Course Schema (`course`)

```sql
-- ============================================================
-- COURSES
-- ============================================================
CREATE TABLE course.courses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instructor_id       UUID NOT NULL,  -- FK to auth.users (cross-schema reference or app-level check)
    title               VARCHAR(300) NOT NULL,
    slug                VARCHAR(300) NOT NULL UNIQUE,
    description         TEXT,
    short_description   VARCHAR(500),
    category            VARCHAR(100),
    difficulty          VARCHAR(20) CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_duration  INTERVAL,
    tags                TEXT[] DEFAULT '{}',
    thumbnail_url       VARCHAR(500),
    is_public_preview   BOOLEAN NOT NULL DEFAULT FALSE,
    max_capacity        INTEGER,  -- NULL = unlimited
    prerequisites       UUID[] DEFAULT '{}',  -- Array of course IDs
    visibility          VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
                        CHECK (visibility IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    current_version_id  UUID,  -- FK to publishing.course_versions (populated when READY)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_courses_instructor ON course.courses(instructor_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_courses_visibility ON course.courses(visibility) WHERE deleted_at IS NULL;
CREATE INDEX idx_courses_category ON course.courses(category) WHERE deleted_at IS NULL;
CREATE INDEX idx_courses_slug ON course.courses(slug);
CREATE INDEX idx_courses_tags ON course.courses USING GIN(tags);

-- ============================================================
-- MODULES
-- ============================================================
CREATE TABLE course.modules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_required     BOOLEAN NOT NULL DEFAULT TRUE,
    estimated_duration INTERVAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_modules_course ON course.modules(course_id);
CREATE UNIQUE INDEX idx_modules_order ON course.modules(course_id, sort_order);

-- ============================================================
-- ASSETS
-- ============================================================
CREATE TABLE course.assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id       UUID NOT NULL REFERENCES course.modules(id) ON DELETE CASCADE,
    title           VARCHAR(300) NOT NULL,
    asset_type      VARCHAR(20) NOT NULL
                    CHECK (asset_type IN ('pdf', 'docx', 'pptx', 'txt', 'md', 'vtt', 'srt')),
    file_name       VARCHAR(500) NOT NULL,
    file_size       BIGINT NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    storage_path    VARCHAR(1000) NOT NULL,  -- MinIO/S3 path
    checksum        VARCHAR(128),            -- SHA-256 for integrity
    sort_order      INTEGER NOT NULL DEFAULT 0,
    upload_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (upload_status IN ('PENDING', 'UPLOADED', 'FAILED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_module ON course.assets(module_id);
```

---

### 1.3 Publishing Schema (`publishing`)

```sql
-- ============================================================
-- COURSE VERSIONS
-- ============================================================
CREATE TABLE publishing.course_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL,  -- FK to course.courses
    version_number  INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PUBLISHING'
                    CHECK (status IN ('PUBLISHING', 'READY', 'FAILED', 'SUPERSEDED')),
    initiated_by    UUID NOT NULL,   -- User who triggered publish
    workflow_id     VARCHAR(255),    -- Temporal workflow ID
    run_id          VARCHAR(255),    -- Temporal run ID
    error_details   JSONB,           -- Failure diagnostics
    total_chunks    INTEGER DEFAULT 0,
    total_assets    INTEGER DEFAULT 0,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ready_at        TIMESTAMPTZ       -- Set when status becomes READY
);

CREATE INDEX idx_versions_course ON publishing.course_versions(course_id);
CREATE INDEX idx_versions_status ON publishing.course_versions(status);
CREATE UNIQUE INDEX idx_versions_course_number ON publishing.course_versions(course_id, version_number);

-- Constraint: at most one PUBLISHING version per course
CREATE UNIQUE INDEX idx_one_publishing_per_course
    ON publishing.course_versions(course_id)
    WHERE status = 'PUBLISHING';

-- ============================================================
-- PUBLISHING JOBS (step-level tracking)
-- ============================================================
CREATE TABLE publishing.publishing_steps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      UUID NOT NULL REFERENCES publishing.course_versions(id) ON DELETE CASCADE,
    step_name       VARCHAR(50) NOT NULL,  -- 'extract', 'chunk', 'embed', 'index', 'finalize'
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}',  -- Step-specific diagnostics
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pub_steps_version ON publishing.publishing_steps(version_id);

-- ============================================================
-- CONTENT CHUNKS (relational reference — full text in Qdrant/MongoDB)
-- ============================================================
CREATE TABLE publishing.chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id      UUID NOT NULL REFERENCES publishing.course_versions(id) ON DELETE CASCADE,
    course_id       UUID NOT NULL,
    module_id       UUID NOT NULL,
    asset_id        UUID NOT NULL,
    chunk_index     INTEGER NOT NULL,
    char_start      INTEGER,
    char_end        INTEGER,
    token_count     INTEGER,
    text_preview    VARCHAR(500),  -- First 500 chars for debugging/admin
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chunks_version ON publishing.chunks(version_id);
CREATE INDEX idx_chunks_course_module ON publishing.chunks(course_id, module_id);
```

---

### 1.4 Enrollment Schema (`enrollment`)

```sql
-- ============================================================
-- ENROLLMENTS
-- ============================================================
CREATE TABLE enrollment.enrollments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL,   -- FK to auth.users
    course_id       UUID NOT NULL,   -- FK to course.courses
    status          VARCHAR(20) NOT NULL DEFAULT 'ENROLLED'
                    CHECK (status IN ('ENROLLED', 'CANCELLED', 'COMPLETED')),
    idempotency_key VARCHAR(255),    -- Client-provided dedup key
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    cancelled_at    TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(student_id, course_id)    -- Prevent duplicate enrollments
);

CREATE INDEX idx_enrollments_student ON enrollment.enrollments(student_id);
CREATE INDEX idx_enrollments_course ON enrollment.enrollments(course_id);
CREATE INDEX idx_enrollments_status ON enrollment.enrollments(status);
CREATE UNIQUE INDEX idx_enrollments_idempotency
    ON enrollment.enrollments(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- ============================================================
-- ENROLLMENT AUDIT
-- ============================================================
CREATE TABLE enrollment.enrollment_audit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id   UUID NOT NULL REFERENCES enrollment.enrollments(id),
    action          VARCHAR(30) NOT NULL,  -- 'ENROLLED', 'CANCELLED', 'COMPLETED', 'PREREQUISITE_CHECK', 'CAPACITY_CHECK'
    actor_id        UUID NOT NULL,
    details         JSONB DEFAULT '{}',
    correlation_id  UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_enrollment_audit_enrollment ON enrollment.enrollment_audit(enrollment_id);
CREATE INDEX idx_enrollment_audit_correlation ON enrollment.enrollment_audit(correlation_id);
```

---

### 1.5 Progress Schema (`progress`)

```sql
-- ============================================================
-- STUDENT PROGRESS (per enrollment)
-- ============================================================
CREATE TABLE progress.student_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id   UUID NOT NULL UNIQUE,  -- FK to enrollment.enrollments
    student_id      UUID NOT NULL,
    course_id       UUID NOT NULL,
    progress_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    status          VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS'
                    CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_student_progress_student ON progress.student_progress(student_id);
CREATE INDEX idx_student_progress_course ON progress.student_progress(course_id);

-- ============================================================
-- MODULE PROGRESS
-- ============================================================
CREATE TABLE progress.module_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_progress_id UUID NOT NULL REFERENCES progress.student_progress(id) ON DELETE CASCADE,
    module_id       UUID NOT NULL,
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    progress_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(student_progress_id, module_id)
);

CREATE INDEX idx_module_progress_parent ON progress.module_progress(student_progress_id);

-- ============================================================
-- CERTIFICATES
-- ============================================================
CREATE TABLE progress.certificates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id   UUID NOT NULL UNIQUE,  -- FK to enrollment.enrollments
    student_id      UUID NOT NULL,
    course_id       UUID NOT NULL,
    course_title    VARCHAR(300) NOT NULL,
    student_name    VARCHAR(200) NOT NULL,
    certificate_number VARCHAR(50) NOT NULL UNIQUE,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB DEFAULT '{}',  -- Additional cert data
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_certificates_student ON progress.certificates(student_id);
CREATE INDEX idx_certificates_number ON progress.certificates(certificate_number);
```

---

### 1.6 Notification Schema (`notification`)

```sql
-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notification.notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    type            VARCHAR(50) NOT NULL,  -- 'enrollment_confirmed', 'course_published', 'course_completed', etc.
    channel         VARCHAR(20) NOT NULL DEFAULT 'in_app'
                    CHECK (channel IN ('in_app', 'email', 'both')),
    title           VARCHAR(300) NOT NULL,
    body            TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                    CHECK (delivery_status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED')),
    retry_count     INTEGER NOT NULL DEFAULT 0,
    correlation_id  UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_user ON notification.notifications(user_id);
CREATE INDEX idx_notifications_unread ON notification.notifications(user_id) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_type ON notification.notifications(type);

-- ============================================================
-- NOTIFICATION PREFERENCES
-- ============================================================
CREATE TABLE notification.notification_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL UNIQUE,
    email_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    enrollment_notifications    BOOLEAN NOT NULL DEFAULT TRUE,
    completion_notifications    BOOLEAN NOT NULL DEFAULT TRUE,
    publishing_notifications    BOOLEAN NOT NULL DEFAULT TRUE,
    admin_notifications         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 1.7 Analytics Schema (`analytics`)

```sql
-- ============================================================
-- EVENT STORE (immutable event log for replay/backfill)
-- ============================================================
CREATE TABLE analytics.event_store (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(100) NOT NULL,
    aggregate_type  VARCHAR(100) NOT NULL,
    aggregate_id    UUID NOT NULL,
    actor_id        UUID,
    payload         JSONB NOT NULL,
    correlation_id  UUID,
    occurred_at     TIMESTAMPTZ NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_type ON analytics.event_store(event_type);
CREATE INDEX idx_events_aggregate ON analytics.event_store(aggregate_type, aggregate_id);
CREATE INDEX idx_events_occurred ON analytics.event_store(occurred_at);

-- Partition by month for performance
-- CREATE TABLE analytics.event_store_2026_04 PARTITION OF analytics.event_store
--     FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- ============================================================
-- DAILY AGGREGATES
-- ============================================================
CREATE TABLE analytics.daily_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date     DATE NOT NULL,
    metric_name     VARCHAR(100) NOT NULL,  -- 'enrollments', 'completions', 'ai_queries', etc.
    dimension_type  VARCHAR(50),            -- 'platform', 'course', 'instructor'
    dimension_id    UUID,                   -- course_id or instructor_id if applicable
    value           BIGINT NOT NULL DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(metric_date, metric_name, dimension_type, COALESCE(dimension_id, '00000000-0000-0000-0000-000000000000'::UUID))
);

CREATE INDEX idx_daily_metrics_date ON analytics.daily_metrics(metric_date);
CREATE INDEX idx_daily_metrics_name ON analytics.daily_metrics(metric_name);

-- ============================================================
-- COURSE METRICS (materialized summary)
-- ============================================================
CREATE TABLE analytics.course_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id           UUID NOT NULL UNIQUE,
    total_enrollments   BIGINT NOT NULL DEFAULT 0,
    active_learners     BIGINT NOT NULL DEFAULT 0,
    completions         BIGINT NOT NULL DEFAULT 0,
    completion_rate     DECIMAL(5,2) DEFAULT 0.00,
    avg_completion_days DECIMAL(10,2),
    ai_queries_total    BIGINT NOT NULL DEFAULT 0,
    ai_queries_answered BIGINT NOT NULL DEFAULT 0,
    ai_queries_refused  BIGINT NOT NULL DEFAULT 0,
    last_updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 1.8 Shared: Outbox Table (per-service)

Each service that publishes events has this table in its schema:

```sql
CREATE TABLE {schema}.outbox (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type  VARCHAR(100) NOT NULL,
    aggregate_id    UUID NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    correlation_id  UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at    TIMESTAMPTZ  -- Set by relay after Kafka publish
);

CREATE INDEX idx_outbox_unpublished ON {schema}.outbox(created_at)
    WHERE published_at IS NULL;
```

---

### 1.9 Shared: Audit Log Table

```sql
CREATE TABLE auth.audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id        UUID,
    actor_type      VARCHAR(20) NOT NULL DEFAULT 'user'
                    CHECK (actor_type IN ('user', 'system', 'admin')),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     UUID,
    old_value       JSONB,
    new_value       JSONB,
    ip_address      INET,
    user_agent      VARCHAR(500),
    correlation_id  UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_actor ON auth.audit_log(actor_id);
CREATE INDEX idx_audit_resource ON auth.audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_action ON auth.audit_log(action);
CREATE INDEX idx_audit_created ON auth.audit_log(created_at);
```

---

## 2. MongoDB Collections

### 2.1 Course Content (Drafts)

```json
// Collection: course_drafts
{
  "_id": "ObjectId",
  "course_id": "UUID string",
  "content": {
    "description_rich": "<html>...",  // Rich text editor content
    "modules": [
      {
        "module_id": "UUID string",
        "content_blocks": [
          {
            "type": "text",
            "body": "..."
          },
          {
            "type": "video_embed",
            "url": "..."
          }
        ],
        "notes": "Instructor notes (not published)"
      }
    ]
  },
  "metadata": {
    "word_count": 5000,
    "last_editor": "UUID string",
    "auto_saved_at": "ISODate"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 2.2 Extracted Content (Post-processing)

```json
// Collection: extracted_content
{
  "_id": "ObjectId",
  "version_id": "UUID string",
  "course_id": "UUID string",
  "asset_id": "UUID string",
  "extraction": {
    "raw_text": "Full extracted text...",
    "language": "en",
    "page_count": 12,
    "extractor": "pdfplumber",
    "extraction_time_ms": 450
  },
  "chunks": [
    {
      "chunk_id": "UUID string",
      "chunk_index": 0,
      "text": "Chunk text content...",
      "char_start": 0,
      "char_end": 512,
      "token_count": 128,
      "metadata": {
        "module_id": "UUID",
        "asset_id": "UUID",
        "page_number": 1,
        "section_title": "Introduction"
      }
    }
  ],
  "created_at": "ISODate"
}
```

### 2.3 AI Job Results

```json
// Collection: ai_jobs
{
  "_id": "ObjectId",
  "job_id": "UUID string",
  "job_type": "summary|objectives|quiz|glossary",
  "course_id": "UUID string",
  "version_id": "UUID string",
  "requested_by": "UUID string",
  "status": "queued|running|completed|failed|cancelled",
  "input": {
    "scope": "course|module",
    "module_id": "UUID string (optional)",
    "parameters": {}
  },
  "result": {
    "content": "Generated content...",
    "citations": [
      {
        "chunk_id": "UUID",
        "text_snippet": "...",
        "module_title": "Module 1",
        "asset_title": "Lecture Notes"
      }
    ],
    "model_used": "nanogpt-v1",
    "tokens_used": {"input": 2000, "output": 500}
  },
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "...",
    "retryable": true
  },
  "created_at": "ISODate",
  "started_at": "ISODate",
  "completed_at": "ISODate"
}
```

---

## 3. Qdrant Collections

### 3.1 Course Chunks Collection

```json
// Collection: course_chunks
// Distance: Cosine
// Vector size: 1536 (OpenAI-compatible embeddings)
{
  "id": "UUID (chunk_id)",
  "vector": [0.123, -0.456, ...],  // 1536-dimensional
  "payload": {
    "course_id": "UUID string",
    "version_id": "UUID string",
    "version_status": "READY",       // Critical: filter on this
    "module_id": "UUID string",
    "module_title": "Introduction to ML",
    "asset_id": "UUID string",
    "asset_title": "Lecture 1 Notes.pdf",
    "chunk_index": 0,
    "text": "The actual chunk text for display/citation...",
    "char_start": 0,
    "char_end": 512,
    "token_count": 128,
    "page_number": 1,
    "section_title": "Introduction"
  }
}
```

**Indexes:**
- Payload index on `course_id` (keyword)
- Payload index on `version_id` (keyword)
- Payload index on `version_status` (keyword)
- Payload index on `module_id` (keyword)

**Query pattern (AI retrieval):**
```json
{
  "vector": [query_embedding],
  "filter": {
    "must": [
      {"key": "course_id", "match": {"value": "<course_id>"}},
      {"key": "version_status", "match": {"value": "READY"}}
    ]
  },
  "limit": 10,
  "with_payload": true
}
```

---

## 4. Redis Key Patterns

| Pattern | Type | TTL | Purpose |
|---------|------|-----|---------|
| `cache:course:{id}:meta` | String (JSON) | 300s | Course metadata cache |
| `cache:catalog:page:{hash}` | String (JSON) | 120s | Catalog page cache |
| `cache:user:{id}:profile` | String (JSON) | 600s | User profile cache |
| `cache:enrolled:{user_id}:{course_id}` | String | 900s | Enrollment check cache |
| `cache:ai:{query_hash}:{course_id}:{version_id}` | String (JSON) | 3600s | AI response cache |
| `ratelimit:{user_id}:{endpoint}` | Sorted Set | Sliding window (60s) | Rate limiting |
| `ratelimit:ai:{user_id}` | Sorted Set | Sliding window (60s) | AI-specific rate limit |
| `idempotency:{key}` | String (JSON) | 86400s | Idempotency key storage |
| `lock:enrollment:{course_id}` | String | 30s | Distributed lock for capacity |
| `session:blacklist:{jti}` | String | Token remaining TTL | Revoked token tracking |

---

## 5. Kafka Event Schemas

### 5.1 Base Envelope

All Kafka messages use this envelope:

```json
{
  "event_id": "UUID",
  "event_type": "EnrollmentCreated",
  "aggregate_type": "enrollment",
  "aggregate_id": "UUID",
  "correlation_id": "UUID",
  "actor_id": "UUID",
  "occurred_at": "ISO8601 timestamp",
  "version": 1,
  "payload": { }
}
```

### 5.2 Key Events

**UserCreated**
```json
{
  "payload": {
    "user_id": "UUID",
    "email": "user@example.com",
    "roles": ["student"],
    "is_verified": false
  }
}
```

**CoursePublishRequested**
```json
{
  "payload": {
    "course_id": "UUID",
    "version_id": "UUID",
    "version_number": 3,
    "initiated_by": "UUID",
    "asset_count": 12
  }
}
```

**CourseReady**
```json
{
  "payload": {
    "course_id": "UUID",
    "version_id": "UUID",
    "version_number": 3,
    "total_chunks": 450,
    "processing_duration_seconds": 180
  }
}
```

**CoursePublishFailed**
```json
{
  "payload": {
    "course_id": "UUID",
    "version_id": "UUID",
    "failed_step": "embed",
    "error_code": "EMBEDDING_API_TIMEOUT",
    "error_message": "Embedding API timed out after 3 retries",
    "retryable": true
  }
}
```

**EnrollmentCreated**
```json
{
  "payload": {
    "enrollment_id": "UUID",
    "student_id": "UUID",
    "course_id": "UUID",
    "course_title": "Introduction to ML"
  }
}
```

**CourseCompleted**
```json
{
  "payload": {
    "enrollment_id": "UUID",
    "student_id": "UUID",
    "course_id": "UUID",
    "certificate_id": "UUID",
    "certificate_number": "SC-2026-00001",
    "completed_at": "ISO8601"
  }
}
```

**AssistantQueryAsked**
```json
{
  "payload": {
    "query_id": "UUID",
    "student_id": "UUID",
    "course_id": "UUID",
    "version_id": "UUID",
    "question_text": "What is gradient descent?",
    "chunks_retrieved": 8,
    "response_status": "answered|refused|error",
    "citations_count": 3,
    "latency_ms": 1500,
    "tokens_used": {"input": 2000, "output": 400}
  }
}
```

---

## 6. Pydantic Schema Examples (Python)

### 6.1 Shared Base

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class EduCorpBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime
```

### 6.2 User Schemas

```python
class UserCreate(BaseModel):
    email: str = Field(..., max_length=255, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)


class UserResponse(EduCorpBase, TimestampMixin):
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]
    avatar_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
```

### 6.3 Course Schemas

```python
class CourseCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = None
    short_description: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=100)
    difficulty: str | None = Field(None, pattern=r'^(beginner|intermediate|advanced)$')
    estimated_duration: str | None = None  # ISO 8601 duration
    tags: list[str] = []
    max_capacity: int | None = Field(None, ge=1)
    prerequisites: list[UUID] = []


class CourseResponse(EduCorpBase, TimestampMixin):
    id: UUID
    instructor_id: UUID
    title: str
    slug: str
    description: str | None
    short_description: str | None
    category: str | None
    difficulty: str | None
    estimated_duration: str | None
    tags: list[str]
    visibility: str
    is_public_preview: bool
    current_version_id: UUID | None
    max_capacity: int | None


class ModuleCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = None
    sort_order: int = Field(0, ge=0)
    is_required: bool = True


class ModuleResponse(EduCorpBase, TimestampMixin):
    id: UUID
    course_id: UUID
    title: str
    description: str | None
    sort_order: int
    is_required: bool
```

### 6.4 Enrollment Schemas

```python
class EnrollmentCreate(BaseModel):
    course_id: UUID
    idempotency_key: str | None = Field(None, max_length=255)


class EnrollmentResponse(EduCorpBase):
    id: UUID
    student_id: UUID
    course_id: UUID
    status: str
    enrolled_at: datetime
    created_at: datetime


class EnrollmentCheckResponse(BaseModel):
    is_enrolled: bool
    enrollment_id: UUID | None = None
    status: str | None = None
```

### 6.5 AI Schemas

```python
class AIQuestionRequest(BaseModel):
    course_id: UUID
    question: str = Field(..., max_length=2000)
    module_id: UUID | None = None  # Optional: scope to module


class AICitation(BaseModel):
    chunk_id: UUID
    module_title: str
    asset_title: str
    text_snippet: str
    page_number: int | None = None


class AIAnswerResponse(BaseModel):
    answer: str
    citations: list[AICitation]
    query_id: UUID
    course_id: UUID
    version_id: UUID
    confidence: str  # 'high', 'medium', 'low'


class AIStreamEvent(BaseModel):
    event: str  # 'token', 'citation', 'done', 'error'
    data: str | dict
```
