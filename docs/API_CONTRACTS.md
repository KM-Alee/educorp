# EduCorp — API Contracts

**Base URL**: `https://api.educorp.dev/api/v1`  
**Auth**: All endpoints (except registration/login) require `Authorization: Bearer <access_token>`  
**Content-Type**: `application/json` (unless file upload)  
**Correlation ID**: All requests accept and return `X-Correlation-Id` header  
**Idempotency**: Write endpoints accept `Idempotency-Key` header  

---

## Standard Response Envelope

### Success
```json
{
  "data": { },
  "meta": {
    "correlation_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Paginated
```json
{
  "data": [],
  "meta": {
    "correlation_id": "uuid",
    "timestamp": "ISO8601"
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Human-readable description",
    "details": { },
    "correlation_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `VALIDATION_ERROR` | 422 | Request body/params validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Entity does not exist |
| `CONFLICT` | 409 | Duplicate resource or state conflict |
| `ENROLLMENT_CAPACITY_EXCEEDED` | 409 | Course is full |
| `ENROLLMENT_PREREQUISITES_NOT_MET` | 409 | Prerequisites incomplete |
| `ENROLLMENT_ALREADY_EXISTS` | 409 | Already enrolled (idempotent return) |
| `COURSE_NOT_READY` | 409 | Course has no READY version |
| `PUBLISHING_IN_PROGRESS` | 409 | Another publish is running |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `AI_PROVIDER_ERROR` | 502 | LLM provider failure |
| `AI_INSUFFICIENT_CONTEXT` | 200 | Not enough course material to answer (returned in response body) |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## 1. Auth Service — `/api/v1/auth`

### POST `/auth/register`
Register a new user account.

**Request:**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123!",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "email": "student@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "is_active": false,
    "is_verified": false,
    "roles": ["student"],
    "created_at": "ISO8601"
  }
}
```

---

### POST `/auth/login`
Authenticate and receive tokens.

**Request:**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "student@example.com",
      "roles": ["student"]
    }
  }
}
```

---

### POST `/auth/refresh`
Rotate refresh token and get new access token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

---

### POST `/auth/verify-email`
Verify email address with token from verification email.

**Request:**
```json
{
  "token": "verification-token-string"
}
```

**Response (200):**
```json
{
  "data": {
    "message": "Email verified successfully"
  }
}
```

---

### POST `/auth/forgot-password`
Request password reset email.

**Request:**
```json
{
  "email": "student@example.com"
}
```

**Response (200):**
```json
{
  "data": {
    "message": "If the email exists, a password reset link has been sent"
  }
}
```

---

### POST `/auth/reset-password`
Reset password with token.

**Request:**
```json
{
  "token": "reset-token-string",
  "new_password": "NewSecurePass456!"
}
```

---

### GET `/auth/me`
Get current user profile. **Auth required.**

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "email": "student@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "is_active": true,
    "is_verified": true,
    "roles": ["student"],
    "avatar_url": null,
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
}
```

---

### PATCH `/auth/me`
Update current user profile. **Auth required.**

**Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "avatar_url": "https://..."
}
```

---

### POST `/auth/instructor-application`
Apply for instructor role. **Auth required (student).**

**Request:**
```json
{
  "reason": "I am a professor at MIT and want to publish my course materials."
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "status": "PENDING",
    "created_at": "ISO8601"
  }
}
```

---

## 2. Admin User Management — `/api/v1/admin/users`
**Auth required: admin role.**

### GET `/admin/users`
List users with filters.

**Query params:** `page`, `page_size`, `role`, `is_active`, `search` (email/name)

---

### PATCH `/admin/users/{user_id}/roles`
Assign or remove roles.

**Request:**
```json
{
  "add_roles": ["instructor"],
  "remove_roles": []
}
```

---

### PATCH `/admin/users/{user_id}/status`
Activate/deactivate user.

**Request:**
```json
{
  "is_active": true
}
```

---

### GET `/admin/instructor-applications`
List pending instructor applications.

**Query params:** `status` (PENDING, APPROVED, REJECTED), `page`, `page_size`

---

### PATCH `/admin/instructor-applications/{id}`
Approve or reject instructor application.

**Request:**
```json
{
  "status": "APPROVED"
}
```

---

## 3. Course Service — `/api/v1/courses`

### POST `/courses`
Create a new course draft. **Auth: instructor.**

**Request:**
```json
{
  "title": "Introduction to Machine Learning",
  "description": "A comprehensive course on ML fundamentals...",
  "short_description": "Learn ML from scratch",
  "category": "Computer Science",
  "difficulty": "beginner",
  "estimated_duration": "PT40H",
  "tags": ["machine-learning", "python", "data-science"],
  "max_capacity": 200,
  "prerequisites": []
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "instructor_id": "uuid",
    "title": "Introduction to Machine Learning",
    "slug": "introduction-to-machine-learning",
    "visibility": "DRAFT",
    "created_at": "ISO8601",
    "...": "..."
  }
}
```

---

### GET `/courses`
Browse courses. Non-privileged callers only see published records; instructors and admins can inspect drafts.

**Query params:**
- `page`, `page_size` (default 20, max 100)
- `category`, `difficulty`
- `instructor_id`
- `search` (keyword search in title/description)
- `visibility` (instructor/admin only: `DRAFT`, `PUBLISHED`, `ARCHIVED`)

---

### GET `/courses/{course_id}`
Get course details for the current draft or published record.

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "title": "Introduction to Machine Learning",
    "slug": "introduction-to-machine-learning",
    "description": "...",
    "category": "Computer Science",
    "difficulty": "beginner",
    "estimated_duration": "PT40H",
    "tags": ["machine-learning"],
    "modules": [
      {
        "id": "uuid",
        "title": "What is ML?",
        "description": "...",
        "sort_order": 0,
        "is_required": true,
        "asset_count": 3
      }
    ],
    "current_version_id": null,
    "max_capacity": 200,
    "is_public_preview": true,
    "visibility": "DRAFT"
  }
}
```

---

### PATCH `/courses/{course_id}`
Update course draft. **Auth: course owner or admin.**

**Request (partial update):**
```json
{
  "title": "Updated Title",
  "tags": ["ml", "ai"]
}
```

---

### DELETE `/courses/{course_id}`
Soft-delete a course. **Auth: course owner or admin.**

---

### POST `/courses/{course_id}/validate`
Run draft validation checks. **Auth: course owner or admin.**

**Response (200):**
```json
{
  "data": {
    "is_valid": false,
    "issues": [
      {
        "field": "modules",
        "message": "At least one module is required",
        "severity": "error"
      }
    ]
  }
}
```

---

### GET `/courses/{course_id}/draft-content`
Read Mongo-backed rich draft content. **Auth: course owner or admin.**

**Response (200):**
```json
{
  "data": {
    "course_id": "uuid",
    "content": {
      "overview": "Draft notes",
      "learning_objectives": ["Explain ML basics"]
    },
    "updated_at": "ISO8601"
  }
}
```

---

### PATCH `/courses/{course_id}/draft-content`
Persist Mongo-backed rich draft content. **Auth: course owner or admin.**

**Request:**
```json
{
  "content": {
    "overview": "Draft notes",
    "learning_objectives": ["Explain ML basics"],
    "lesson_notes": []
  }
}
```

---

## 4. Module Endpoints — `/api/v1/courses/{course_id}/modules`

### POST `/courses/{course_id}/modules`
Add module to course. **Auth: course owner.**

**Request:**
```json
{
  "title": "Introduction to Neural Networks",
  "description": "Cover the basics of neural network architecture",
  "sort_order": 2,
  "is_required": true
}
```

---

### GET `/courses/{course_id}/modules`
List all modules for a course.

---

### PATCH `/courses/{course_id}/modules/{module_id}`
Update module. **Auth: course owner.**

---

### DELETE `/courses/{course_id}/modules/{module_id}`
Delete module. **Auth: course owner. Only in DRAFT state.**

---

### PATCH `/courses/{course_id}/modules/reorder`
Reorder modules. **Auth: course owner.**

**Request:**
```json
{
  "order": ["uuid-module-1", "uuid-module-3", "uuid-module-2"]
}
```

---

## 5. Asset Endpoints — `/api/v1/courses/{course_id}/modules/{module_id}/assets`

### POST `/courses/{course_id}/modules/{module_id}/assets/upload`
Upload an asset file. **Auth: course owner.** Content-Type: `multipart/form-data`.

**Form fields:**
- `file`: The file (PDF, DOCX, PPTX, TXT, MD, VTT, SRT)
- `title`: Asset title (string)
- `sort_order`: Integer (optional)

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "title": "Lecture 1 Notes",
    "asset_type": "pdf",
    "file_name": "lecture-1.pdf",
    "file_size": 1048576,
    "upload_status": "UPLOADED",
    "storage_path": "course-assets/uuid/uuid/lecture-1.pdf"
  }
}
```

---

### GET `/courses/{course_id}/modules/{module_id}/assets`
List assets for a module.

---

### GET `/courses/{course_id}/modules/{module_id}/assets/{asset_id}/download`
Get presigned download URL. **Auth: enrolled student, course owner, or admin.**

**Response (200):**
```json
{
  "data": {
    "download_url": "https://minio.../presigned-url",
    "expires_in": 3600
  }
}
```

---

### DELETE `/courses/{course_id}/modules/{module_id}/assets/{asset_id}`
Delete asset. **Auth: course owner. Only in DRAFT state.**

---

## 6. Publishing Service — `/api/v1/publishing`

### POST `/courses/{course_id}/publish`
Trigger course publishing. **Auth: course owner or admin.**

**Request:**
```json
{
  "idempotency_key": "pub-2026-04-11-abc123"
}
```

**Response (202):**
```json
{
  "data": {
    "version_id": "uuid",
    "version_number": 3,
    "status": "PUBLISHING",
    "workflow_id": "temporal-workflow-id",
    "message": "Publishing started. Monitor status via GET /publishing/versions/{version_id}"
  }
}
```

---

### GET `/publishing/versions/{version_id}`
Get publishing status. **Auth: course owner or admin.**

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "course_id": "uuid",
    "version_number": 3,
    "status": "PUBLISHING",
    "steps": [
      {"step": "validate", "status": "COMPLETED", "duration_ms": 200},
      {"step": "extract", "status": "COMPLETED", "duration_ms": 15000},
      {"step": "chunk", "status": "RUNNING", "started_at": "ISO8601"},
      {"step": "embed", "status": "PENDING"},
      {"step": "index", "status": "PENDING"},
      {"step": "finalize", "status": "PENDING"}
    ],
    "total_assets": 12,
    "processing_started_at": "ISO8601"
  }
}
```

---

### GET `/courses/{course_id}/versions`
List all versions for a course. **Auth: course owner or admin.**

---

### POST `/publishing/versions/{version_id}/retry`
Retry a failed publishing job. **Auth: course owner or admin.**

---

### POST `/publishing/versions/{version_id}/cancel`
Cancel an in-progress publishing job. **Auth: admin.**

---

## 7. Enrollment Service — `/api/v1/enrollments`

### POST `/enrollments`
Enroll in a course. **Auth: student.**

**Request:**
```json
{
  "course_id": "uuid",
  "idempotency_key": "enroll-uuid-abc123"
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "student_id": "uuid",
    "course_id": "uuid",
    "status": "ENROLLED",
    "enrolled_at": "ISO8601"
  }
}
```

**Error (409 — already enrolled, idempotent return):**
```json
{
  "data": {
    "id": "existing-enrollment-uuid",
    "student_id": "uuid",
    "course_id": "uuid",
    "status": "ENROLLED",
    "enrolled_at": "ISO8601"
  },
  "meta": {
    "idempotent_hit": true
  }
}
```

---

### GET `/enrollments`
List current user's enrollments. **Auth required.**

**Query params:** `status` (ENROLLED, COMPLETED, CANCELLED), `page`, `page_size`

---

### GET `/enrollments/{enrollment_id}`
Get enrollment details.

---

### POST `/enrollments/{enrollment_id}/cancel`
Cancel enrollment. **Auth: student (self) or admin.**

---

### GET `/courses/{course_id}/enrollment-status`
Check if current user is enrolled. **Auth required.**

**Response (200):**
```json
{
  "data": {
    "is_enrolled": true,
    "enrollment_id": "uuid",
    "status": "ENROLLED",
    "progress_percent": 45.5
  }
}
```

---

## 8. Progress Service — `/api/v1/progress`

### GET `/progress/enrollments/{enrollment_id}`
Get detailed progress for an enrollment. **Auth: student (self) or admin.**

**Response (200):**
```json
{
  "data": {
    "enrollment_id": "uuid",
    "course_id": "uuid",
    "progress_percent": 45.50,
    "status": "IN_PROGRESS",
    "started_at": "ISO8601",
    "last_activity_at": "ISO8601",
    "modules": [
      {
        "module_id": "uuid",
        "module_title": "Introduction",
        "is_completed": true,
        "progress_percent": 100.0,
        "completed_at": "ISO8601"
      },
      {
        "module_id": "uuid",
        "module_title": "Neural Networks",
        "is_completed": false,
        "progress_percent": 30.0
      }
    ]
  }
}
```

---

### POST `/progress/enrollments/{enrollment_id}/modules/{module_id}/complete`
Mark a module as complete. **Auth: student (self).**

**Response (200):**
```json
{
  "data": {
    "module_id": "uuid",
    "is_completed": true,
    "completed_at": "ISO8601",
    "overall_progress_percent": 66.67,
    "course_completed": false
  }
}
```

**When course completes (all required modules done):**
```json
{
  "data": {
    "module_id": "uuid",
    "is_completed": true,
    "completed_at": "ISO8601",
    "overall_progress_percent": 100.0,
    "course_completed": true,
    "certificate": {
      "id": "uuid",
      "certificate_number": "SC-2026-00042",
      "issued_at": "ISO8601"
    }
  }
}
```

---

### GET `/progress/dashboard`
Get student's progress dashboard. **Auth: student.**

**Response (200):**
```json
{
  "data": {
    "active_courses": 3,
    "completed_courses": 5,
    "total_certificates": 5,
    "courses": [
      {
        "course_id": "uuid",
        "course_title": "Intro to ML",
        "progress_percent": 45.5,
        "status": "IN_PROGRESS",
        "last_activity_at": "ISO8601"
      }
    ]
  }
}
```

---

### GET `/progress/certificates`
List all earned certificates. **Auth: student.**

---

### GET `/progress/certificates/{certificate_id}`
Get certificate detail (for verification). **Public endpoint.**

---

## 9. AI Service — `/api/v1/ai`

### POST `/ai/ask`
Ask a question about an enrolled course. **Auth: enrolled student.**

**Request:**
```json
{
  "course_id": "uuid",
  "question": "What is the difference between supervised and unsupervised learning?",
  "module_id": null
}
```

**Response (200) — non-streaming:**
```json
{
  "data": {
    "query_id": "uuid",
    "answer": "Based on the course materials, supervised learning uses labeled data...",
    "citations": [
      {
        "chunk_id": "uuid",
        "module_title": "Types of Machine Learning",
        "asset_title": "Lecture 2 Notes.pdf",
        "text_snippet": "Supervised learning is a paradigm where...",
        "page_number": 5
      },
      {
        "chunk_id": "uuid",
        "module_title": "Types of Machine Learning",
        "asset_title": "Lecture 2 Notes.pdf",
        "text_snippet": "In contrast, unsupervised learning does not...",
        "page_number": 7
      }
    ],
    "confidence": "high",
    "course_id": "uuid",
    "version_id": "uuid"
  }
}
```

---

### GET `/ai/ask/stream` (SSE)
Streaming version. **Auth: enrolled student.**

**Query params:** `course_id`, `question`, `module_id` (optional)

**SSE events:**
```
event: token
data: {"text": "Based on"}

event: token
data: {"text": " the course"}

event: citation
data: {"chunk_id": "uuid", "module_title": "...", "asset_title": "...", "text_snippet": "...", "page_number": 5}

event: done
data: {"query_id": "uuid", "confidence": "high", "total_citations": 2}

event: error
data: {"code": "AI_PROVIDER_ERROR", "message": "LLM provider unavailable"}
```

---

### POST `/ai/ask/clarify`
When the assistant needs clarification. **Auth: enrolled student.**

**Request:**
```json
{
  "course_id": "uuid",
  "original_query_id": "uuid",
  "clarification": "I meant specifically for image classification"
}
```

---

## 10. AI Instructor Tools — `/api/v1/ai/instructor`

### POST `/ai/instructor/enhance`
Request content enhancement. **Auth: course owner.**

**Request:**
```json
{
  "course_id": "uuid",
  "job_type": "summary",
  "scope": "module",
  "module_id": "uuid",
  "parameters": {
    "max_length": 500,
    "style": "academic"
  }
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "uuid",
    "status": "QUEUED",
    "message": "Enhancement job queued. Poll GET /ai/instructor/jobs/{job_id}"
  }
}
```

---

### GET `/ai/instructor/enhance/stream` (SSE)
Streaming enhancement (for interactive use). **Auth: course owner.**

**Query params:** `course_id`, `job_type`, `scope`, `module_id`

---

### GET `/ai/instructor/jobs/{job_id}`
Poll job status. **Auth: course owner.**

**Response (200):**
```json
{
  "data": {
    "job_id": "uuid",
    "job_type": "quiz",
    "status": "COMPLETED",
    "result": {
      "questions": [
        {
          "question": "What is the primary goal of supervised learning?",
          "type": "mcq",
          "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
          "correct_answer": "B",
          "explanation": "...",
          "citation": {
            "module_title": "Types of ML",
            "asset_title": "Lecture 2",
            "page_number": 3
          }
        }
      ]
    },
    "created_at": "ISO8601",
    "completed_at": "ISO8601"
  }
}
```

---

### POST `/ai/instructor/jobs/{job_id}/cancel`
Cancel a queued/running job. **Auth: course owner.**

---

### GET `/ai/instructor/jobs`
List enhancement jobs. **Auth: course owner.**

**Query params:** `course_id`, `status`, `job_type`, `page`, `page_size`

---

## 11. Search Service — `/api/v1/search`

### GET `/search/courses`
Keyword search across course catalog.

**Query params:**
- `q` (search query, required)
- `category`, `difficulty`, `tags`
- `page`, `page_size`

**Response (200):**
```json
{
  "data": [
    {
      "course_id": "uuid",
      "title": "Introduction to ML",
      "short_description": "...",
      "instructor_name": "Dr. Smith",
      "category": "Computer Science",
      "difficulty": "beginner",
      "relevance_score": 0.95,
      "matched_in": ["title", "description"]
    }
  ],
  "pagination": {}
}
```

---

### POST `/search/semantic`
Semantic search within a course (internal, used by AI service). **Auth: service-to-service.**

**Request:**
```json
{
  "course_id": "uuid",
  "query": "gradient descent optimization",
  "top_k": 10,
  "module_id": null,
  "version_status": "READY"
}
```

**Response (200):**
```json
{
  "data": {
    "chunks": [
      {
        "chunk_id": "uuid",
        "text": "Gradient descent is an iterative optimization...",
        "score": 0.92,
        "module_id": "uuid",
        "module_title": "Optimization",
        "asset_id": "uuid",
        "asset_title": "Lecture 5.pdf",
        "page_number": 12,
        "chunk_index": 45
      }
    ],
    "query_embedding_model": "text-embedding-ada-002",
    "total_results": 10
  }
}
```

---

## 12. Notification Service — `/api/v1/notifications`

### GET `/notifications`
List current user's notifications. **Auth required.**

**Query params:** `is_read` (bool), `type`, `page`, `page_size`

---

### PATCH `/notifications/{notification_id}/read`
Mark notification as read. **Auth required.**

---

### POST `/notifications/read-all`
Mark all notifications as read. **Auth required.**

---

### GET `/notifications/preferences`
Get notification preferences. **Auth required.**

---

### PATCH `/notifications/preferences`
Update notification preferences. **Auth required.**

**Request:**
```json
{
  "email_enabled": true,
  "enrollment_notifications": true,
  "completion_notifications": true
}
```

---

## 13. Analytics Service — `/api/v1/analytics`

### GET `/analytics/platform`
Platform-wide metrics. **Auth: admin.**

**Query params:** `from_date`, `to_date`, `granularity` (day, week, month)

**Response (200):**
```json
{
  "data": {
    "period": {"from": "2026-04-01", "to": "2026-04-11"},
    "total_students": 5000,
    "total_instructors": 120,
    "total_courses": 350,
    "enrollments": {
      "total": 15000,
      "period": 1200,
      "timeseries": [{"date": "2026-04-01", "count": 150}, "..."]
    },
    "completions": {
      "total": 3200,
      "period": 280,
      "rate": 21.3
    },
    "ai_usage": {
      "total_queries": 45000,
      "period_queries": 5000,
      "answer_rate": 88.5,
      "refusal_rate": 8.2,
      "error_rate": 3.3,
      "avg_latency_ms": 1800
    }
  }
}
```

---

### GET `/analytics/courses/{course_id}`
Course-specific analytics. **Auth: course owner or admin.**

**Response (200):**
```json
{
  "data": {
    "course_id": "uuid",
    "course_title": "Intro to ML",
    "total_enrollments": 350,
    "active_learners": 180,
    "completions": 95,
    "completion_rate": 27.1,
    "avg_completion_days": 14.5,
    "ai_queries": 2400,
    "ai_answer_rate": 90.2,
    "module_breakdown": [
      {
        "module_id": "uuid",
        "module_title": "Introduction",
        "completion_rate": 85.0
      }
    ]
  }
}
```

---

### GET `/analytics/instructor/{instructor_id}`
Instructor analytics. **Auth: instructor (self) or admin.**

---

## 14. Health & Admin Ops — `/api/v1/admin`

### GET `/health/live`
Liveness probe. **No auth.**

### GET `/health/ready`
Readiness probe. **No auth.**

---

### GET `/admin/workflows`
List Temporal workflows. **Auth: admin.**

**Query params:** `status`, `course_id`, `page`, `page_size`

---

### GET `/admin/workflows/{workflow_id}`
Get workflow detail. **Auth: admin.**

---

### POST `/admin/workflows/{workflow_id}/retry`
Retry failed workflow. **Auth: admin.**

---

### GET `/admin/dlq`
View dead letter queue messages. **Auth: admin.**

**Query params:** `topic`, `page`, `page_size`

---

### POST `/admin/dlq/{message_id}/replay`
Replay a DLQ message. **Auth: admin.**

---

### GET `/admin/audit-log`
Search audit log. **Auth: admin.**

**Query params:** `actor_id`, `action`, `resource_type`, `resource_id`, `from_date`, `to_date`, `page`, `page_size`

---

## Rate Limiting

| Endpoint Group | Limit | Window |
|---------------|-------|--------|
| Auth (login/register) | 10 req | 1 min per IP |
| General API | 100 req | 1 min per user |
| AI Ask (Q&A) | 20 req | 1 min per user |
| AI Instructor Tools | 10 req | 1 min per user |
| File Upload | 30 req | 10 min per user |
| Search | 60 req | 1 min per user |
| Admin | 200 req | 1 min per user |

Rate limit headers returned on every response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1713000000
```
