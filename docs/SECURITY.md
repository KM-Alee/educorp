# EduCorp — Security Design

## 1. Authentication

### 1.1 Password Security

| Aspect | Implementation |
|--------|---------------|
| Hashing | **Argon2id** (preferred) via `passlib[argon2]`, fallback to bcrypt |
| Minimum length | 8 characters |
| Complexity | At least 1 uppercase, 1 lowercase, 1 digit (enforced via Pydantic validator) |
| Breached password check | Optional: check against HaveIBeenPwned API (k-anonymity model) |
| Rate limiting | 10 login attempts per minute per IP; lockout after 5 consecutive failures (15 min) |

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)
```

### 1.2 JWT Token Architecture

**Access Token** (short-lived):
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": ["student"],
  "iat": 1713000000,
  "exp": 1713000900,
  "jti": "unique-token-id",
  "iss": "educorp",
  "aud": "educorp-api"
}
```

**Refresh Token** (long-lived):
- Stored as SHA-256 hash in database (never store raw tokens)
- Rotated on every use (old token immediately invalidated)
- Bound to device/IP for anomaly detection
- Revocable via database delete

**Token Lifecycle**:
```
Access Token:  15 min TTL
Refresh Token: 7 days TTL, rotate on use
```

**Signing**: HS256 with a 256-bit secret (env: `JWT_SECRET_KEY`). Migrate to RS256 (asymmetric) if services need to validate without sharing the secret.

### 1.3 Token Validation Flow

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> UserTokenPayload:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience="educorp-api",
            issuer="educorp",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, detail="Invalid token")

    # Check token not revoked (jti in blacklist)
    if await is_token_revoked(payload["jti"]):
        raise HTTPException(401, detail="Token revoked")

    return UserTokenPayload(**payload)
```

### 1.4 Token Revocation

- On logout: add token's `jti` to Redis blacklist with remaining TTL
- On password change: revoke all refresh tokens for the user
- On role change: revoke all tokens (force re-login)

## 2. Authorization (RBAC)

### 2.1 Role Hierarchy

```
admin > instructor > student
```

Admin inherits all instructor and student permissions. Instructors do NOT inherit student permissions automatically — they must also have the student role to enroll in courses.

### 2.2 Permission Matrix

| Resource / Action | Student | Instructor | Admin |
|-------------------|---------|------------|-------|
| Register/Login | ✅ | ✅ | ✅ |
| View own profile | ✅ | ✅ | ✅ |
| Browse READY courses | ✅ | ✅ | ✅ |
| Enroll in course | ✅ | ✅* | ✅ |
| View enrolled content | ✅ | ✅ | ✅ |
| Track progress | ✅ | ✅ | ✅ |
| AI Q&A (enrolled) | ✅ | ✅ | ✅ |
| Create course | ❌ | ✅ | ✅ |
| Edit own course | ❌ | ✅ | ✅ |
| Upload assets | ❌ | ✅ | ✅ |
| Publish course | ❌ | ✅ | ✅ |
| AI instructor tools | ❌ | ✅ (own courses) | ✅ |
| View course analytics | ❌ | ✅ (own courses) | ✅ |
| Manage users | ❌ | ❌ | ✅ |
| Manage roles | ❌ | ❌ | ✅ |
| Approve instructors | ❌ | ❌ | ✅ |
| View platform analytics | ❌ | ❌ | ✅ |
| Admin ops (workflows) | ❌ | ❌ | ✅ |

*Instructors need student role to enroll.

### 2.3 Role Enforcement

```python
from functools import wraps
from fastapi import HTTPException


def require_roles(*allowed_roles: str):
    """Dependency that checks user has at least one of the specified roles."""
    async def check_roles(user: UserTokenPayload = Depends(get_current_user)):
        if not any(role in user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {allowed_roles}"
            )
        return user
    return check_roles


# Usage in routes
@router.post("/courses")
async def create_course(
    body: CourseCreate,
    user: UserTokenPayload = Depends(require_roles("instructor", "admin")),
):
    ...
```

### 2.4 Resource-Level Authorization

Beyond role checks, some endpoints require **ownership verification**:

```python
async def require_course_owner(
    course_id: UUID,
    user: UserTokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Course:
    course = await course_repo.get_by_id(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if "admin" not in user.roles and course.instructor_id != user.sub:
        raise HTTPException(403, "Not the course owner")
    return course
```

### 2.5 Entitlement Checks (Content Access)

Before serving course content or AI responses:

```python
async def verify_entitlement(
    user_id: UUID,
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Check if user can access course content."""
    # Admin can access everything
    if "admin" in user.roles:
        return True

    # Instructor can access own courses
    course = await course_repo.get_by_id(db, course_id)
    if course and course.instructor_id == user_id:
        return True

    # Student must be enrolled
    enrollment = await enrollment_repo.get_active(db, user_id, course_id)
    if enrollment and enrollment.status in ("ENROLLED", "COMPLETED"):
        return True

    # Public preview — allow metadata and first module
    if course and course.is_public_preview:
        return True  # Limited access handled at response level

    return False
```

## 3. API Security

### 3.1 Input Validation

All request inputs validated via Pydantic models:
- String length limits on all text fields
- Email format validation with regex
- UUID format validation
- Enum validation for status fields
- File type validation for uploads (MIME type + extension + magic bytes)
- Query parameter bounds (page_size max 100, etc.)

```python
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=10000)
    tags: list[str] = Field(default=[], max_length=20)  # Max 20 tags

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        for tag in v:
            if len(tag) > 50 or not re.match(r'^[a-zA-Z0-9\-]+$', tag):
                raise ValueError(f"Invalid tag: {tag}")
        return v
```

### 3.2 SQL Injection Prevention

- **SQLAlchemy ORM**: parameterized queries by default
- **No raw SQL**: all database access through SQLAlchemy models and ORM queries
- **Alembic migrations**: schema changes via migration scripts, never ad-hoc DDL

### 3.3 File Upload Security

```python
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md", ".vtt", ".srt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
    "text/vtt",
    "application/x-subrip",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

async def validate_upload(file: UploadFile) -> None:
    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, f"File type {ext} not allowed")

    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(422, f"MIME type {file.content_type} not allowed")

    # Check file size (read first chunk to validate)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(422, f"File exceeds {MAX_FILE_SIZE // (1024*1024)} MB limit")

    # Validate magic bytes (file signature)
    if ext == ".pdf" and not content[:4] == b"%PDF":
        raise HTTPException(422, "File content does not match PDF format")

    await file.seek(0)  # Reset for further processing
```

### 3.4 Rate Limiting

Implemented via Redis sliding window:

```python
import time
from redis.asyncio import Redis


async def check_rate_limit(
    redis: Redis,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Returns (allowed: bool, remaining: int).
    Uses Redis sorted set with timestamps as scores.
    """
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # Remove expired entries
    pipe.zadd(key, {str(now): now})               # Add current request
    pipe.zcard(key)                                # Count requests in window
    pipe.expire(key, window_seconds)               # Set key expiry
    results = await pipe.execute()

    current_count = results[2]
    allowed = current_count <= max_requests
    remaining = max(0, max_requests - current_count)

    return allowed, remaining
```

### 3.5 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Configurable per environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-Id", "Idempotency-Key"],
    expose_headers=["X-Correlation-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=86400,
)
```

## 4. Data Security

### 4.1 Encryption

| Data | At Rest | In Transit |
|------|---------|-----------|
| Passwords | Argon2id hash (irreversible) | HTTPS |
| JWT tokens | N/A (ephemeral) | HTTPS |
| Refresh tokens | SHA-256 hash in DB | HTTPS |
| Database | PostgreSQL TDE (prod) / volume encryption | TLS connections (prod) |
| Object storage | MinIO server-side encryption | HTTPS (prod) |
| Redis | Not encrypted at rest (cache only) | TLS (prod) |
| Kafka | Not encrypted at rest (dev) | TLS (prod) |

### 4.2 Secrets Management

- **Development**: `.env` file (git-ignored)
- **Production**: Use a secrets manager (Vault, AWS Secrets Manager, etc.)
- **Docker**: Use Docker secrets or environment variables via compose
- **Never commit**: API keys, JWT secrets, database passwords
- `.env.example` contains placeholder values only

### 4.3 PII Handling

| Field | Logged? | Trace Context? | Analytics? |
|-------|---------|---------------|-----------|
| Email | ❌ (masked: `j***@example.com`) | ❌ | Hashed |
| Name | ❌ | ❌ | ❌ |
| Password | ❌ Never | ❌ | ❌ |
| IP Address | ❌ (last octet masked in logs) | ❌ | ❌ |
| User ID | ✅ | ✅ | ✅ |
| Course ID | ✅ | ✅ | ✅ |
| AI Questions | ❌ (hash only in logs) | ❌ | Hash + metadata only |

```python
def mask_email(email: str) -> str:
    """Mask email for logging: jane.doe@example.com → j***@example.com"""
    local, domain = email.split("@")
    return f"{local[0]}***@{domain}"
```

### 4.4 Data Retention

| Data Type | Retention | Deletion Method |
|-----------|-----------|----------------|
| User accounts | Until deleted by user/admin | Soft delete, then hard delete after 30 days |
| Audit logs | 3 years (configurable) | Automated purge job |
| AI prompts/responses | 90 days (configurable) | Automated purge + anonymization |
| Kafka events | 7 days (topic retention) | Automatic by Kafka |
| Analytics events | 2 years | Partition drop |
| Course content | While course exists | Cascade delete with course |
| Certificates | Permanent | Not deleted (legal requirement) |

### 4.5 Right to Delete (GDPR-style)

When a user requests deletion:
1. Soft-delete user record
2. Anonymize: replace PII with `[DELETED_USER_{uuid}]`
3. Revoke all tokens
4. Delete notification preferences and in-app notifications
5. Retain: enrollments (anonymized), certificates (anonymized), analytics (aggregated)
6. After 30-day grace period: hard-delete user record
7. Emit `UserDeleted` event for downstream services

## 5. Infrastructure Security

### 5.1 Network Isolation

- Services communicate only within the Docker network
- Only Traefik exposes ports to the host
- Database ports exposed only for development (remove in production)
- Inter-service calls are HTTP within the trusted network (no mTLS in dev; add for production)

### 5.2 Container Security

- All service containers run as non-root user (`appuser`)
- Read-only filesystem where possible
- No `--privileged` flag
- Minimal base images (`python:3.12-slim`)
- Regular image vulnerability scanning (Trivy, Snyk)

### 5.3 Dependency Security

- `uv` lockfile (`uv.lock`) ensures reproducible builds
- Weekly dependency audit: `pip-audit` or `safety check`
- Dependabot / Renovate for automated updates
- Pin all production dependencies to exact versions

## 6. Idempotency

### 6.1 Implementation

Write endpoints accept `Idempotency-Key` header:

```python
async def check_idempotency(
    idempotency_key: str | None,
    redis: Redis,
) -> dict | None:
    """Check if this request was already processed."""
    if not idempotency_key:
        return None

    key = f"idempotency:{idempotency_key}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None


async def store_idempotency(
    idempotency_key: str,
    response: dict,
    redis: Redis,
    ttl: int = 86400,  # 24 hours
) -> None:
    """Store the response for this idempotency key."""
    key = f"idempotency:{idempotency_key}"
    await redis.setex(key, ttl, json.dumps(response))
```

### 6.2 Critical Idempotent Endpoints

| Endpoint | Idempotency Mechanism |
|----------|----------------------|
| `POST /enrollments` | `Idempotency-Key` header + DB unique constraint (student_id, course_id) |
| `POST /courses/{id}/publish` | `Idempotency-Key` + unique partial index (one PUBLISHING per course) |
| `POST /progress/.../complete` | DB unique constraint (progress_id, module_id) |

## 7. Security Headers

Set via Traefik middleware or within FastAPI:

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"  # Modern browsers handle this
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
```
