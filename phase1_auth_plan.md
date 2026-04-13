# Phase 1 Auth Implementation Plan

## Goal
Implement Phase 1 (Authentication & User Management) for auth-service using the defined API contracts, data models, security rules, and project conventions. Focus on correctness, async behavior, response envelopes, RBAC, and event/audit logging.

## Scope (from docs)
- Endpoints: register, login, refresh, verify email, forgot/reset password, me GET/PATCH, instructor application, admin users list/roles/status, admin instructor applications list/review.
- Tables: auth.users, roles, user_roles, refresh_tokens, password_resets, email_verifications, instructor_applications, audit_log, outbox (per-service).
- Security: Argon2id hashing, password complexity, JWT access (15m), refresh (7d) with rotation, refresh token stored hashed, rate limiting and lockout on login.
- Events: write to auth outbox, publish on user.lifecycle via relay.

## Implementation Steps

### 1) Settings and constants
- Extend [services/auth/app/config.py](services/auth/app/config.py) with auth-specific settings:
  - `jwt_secret_key`, `jwt_algorithm`, `jwt_issuer`, `jwt_audience`
  - `access_token_ttl_minutes`, `refresh_token_ttl_days`
  - password policy settings (min length, complexity)
  - rate limit and lockout config (max attempts, window, lockout duration)
- Keep defaults aligned with [docs/SECURITY.md](docs/SECURITY.md).

### 2) Data models (SQLAlchemy 2.0)
Create models in `services/auth/app/models/` using `UUIDPrimaryKeyMixin`, `TimestampMixin`, `SoftDeleteMixin` as appropriate, and `__table_args__ = {"schema": "auth"}`.
- `User` (users)
- `Role` (roles)
- `UserRole` (user_roles)
- `RefreshToken` (refresh_tokens)
- `PasswordReset` (password_resets)
- `EmailVerification` (email_verifications)
- `InstructorApplication` (instructor_applications)
- `AuditLog` (audit_log)
- `OutboxEvent` (outbox)

Notes:
- Indexes and constraints must match [docs/DATA_MODELS.md](docs/DATA_MODELS.md), including partial indexes and unique constraints.
- Avoid eager relationship loading; use explicit joins in repositories to prevent hidden queries.

### 3) Alembic migration
- Add a new migration in `services/auth/alembic/versions/` to create all auth tables + indexes + constraints.
- Ensure upgrade/downgrade functions are complete and `schema="auth"` is used for all tables.

### 4) Auth utilities (shared)
Create reusable helpers in `shared/educorp_common/auth/`:
- `passwords.py`: Argon2id `CryptContext`, `hash_password()`, `verify_password()`, and optional validator helpers.
- `tokens.py`:
  - `create_access_token(payload)` and `decode_access_token(token)`
  - `create_refresh_token()` -> random string + SHA-256 hash storage helper
  - `verify_refresh_token(raw_token, stored_hash)`
  - include `jti`, `iss`, `aud`, and `exp` in access tokens
- Re-export from `shared/educorp_common/auth/__init__.py` as needed.

### 5) Auth dependencies (shared)
Update [shared/educorp_common/auth/dependencies.py](shared/educorp_common/auth/dependencies.py):
- Use `HTTPBearer` to read access tokens.
- Validate JWT (issuer/audience/exp) via shared utilities.
- Load user and roles from DB to enforce `is_active` / `is_verified` and ensure roles are current.
- Keep `require_roles(*roles)` working with updated `CurrentUser`.

### 6) Repositories (auth-service)
Create repository classes in `services/auth/app/repositories/`:
- `UserRepository`: get by id/email, create user, update profile, set active/verified, list with filters.
- `RoleRepository` + `UserRoleRepository`: role lookup, add/remove roles, list roles by user.
- `RefreshTokenRepository`: store hash, revoke, rotate, lookup by hash.
- `PasswordResetRepository`: create token, mark used.
- `EmailVerificationRepository`: create token, mark verified.
- `InstructorApplicationRepository`: create, list, update status.
- `AuditLogRepository`: create audit entries.
- `OutboxRepository`: create outbox events (no Kafka publish here).

All repositories accept `AsyncSession`, use `flush()` not `commit()`.

### 7) Services (auth-service)
Implement service layer in `services/auth/app/services/`:
- `AuthService`:
  - `register()` -> create user, assign student role, create email verification token, audit + outbox
  - `verify_email()` -> verify token, activate user, audit + outbox
  - `login()` -> password check, is_active/is_verified, rate limit + lockout, issue tokens, store refresh hash, audit
  - `refresh()` -> verify refresh token, rotate, revoke old, issue new, audit
  - `forgot_password()` -> create reset token if user exists, return generic response, audit + outbox
  - `reset_password()` -> validate token, update password, revoke refresh tokens, audit
  - `get_me()` / `update_me()` -> profile access
- `AdminUserService`:
  - list users with filters
  - set roles (add/remove) -> revoke refresh tokens, audit + outbox
  - set status (activate/deactivate) -> audit + outbox
- `InstructorApplicationService`:
  - create application
  - list applications (admin)
  - review (approve/reject) -> add instructor role if approved, audit + outbox

### 8) Rate limiting and lockout
- Use Redis to track login attempts per email + IP.
- Enforce 10 attempts/min, lock for 15 minutes after 5 failures (per [docs/SECURITY.md](docs/SECURITY.md)).
- Implement helper in auth service or shared auth utils to keep login flow clean.

### 9) API routes and schemas
Create schemas in `services/auth/app/schemas/`:
- Requests: Register, Login, Refresh, VerifyEmail, ForgotPassword, ResetPassword, UpdateMe, InstructorApplication, AdminRoleUpdate, AdminStatusUpdate.
- Responses: UserOut, TokenResponse, InstructorApplicationOut, MessageOut, AdminUserListOut, etc.
- Include Pydantic validators for password complexity.

Create routers in `services/auth/app/api/v1/`:
- `auth.py`: register, login, refresh, verify email, forgot/reset, me endpoints, instructor application.
- `admin.py`: user list, role/status updates, instructor application review.
- Update [services/auth/app/api/v1/__init__.py](services/auth/app/api/v1/__init__.py) to include routers.

Use `SuccessResponse[...]` for response envelopes; raise `EduCorpError` with codes from [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md).

### 10) Audit log + outbox
- Create audit entries for key actions (register, login, verify, reset, role/status changes, instructor app review).
- Write outbox events in the same DB transaction as the change. Use `event_type` values under `user.lifecycle` (e.g., `user.created`, `user.verified`, `user.role_changed`, `user.instructor_application.reviewed`).
- Include `correlation_id` from `get_correlation_id()` and `source_service="auth"` in metadata.

### 11) Seed script
- Add `services/auth/scripts/seed.py` (and `__init__.py`) to create default roles and an admin user.
- Ensure idempotency (skip if roles/users already exist).
- Align with `make seed` target in [Makefile](Makefile).

### 12) Tests
Follow [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) and [testing.instructions.md](.github/instructions/testing.instructions.md):
- `services/auth/tests/factories.py`: User, Role, UserRole, tokens, applications.
- Unit tests: password hashing, JWT create/verify, role checks, rate limit helpers.
- Integration tests (httpx AsyncClient):
  - Register: success, duplicate email -> 409, validation -> 422
  - Login: success, wrong password -> 401, unverified/disabled -> 403/401 per contract
  - Refresh: success, rotation, reuse -> 401
  - Verify email: success, expired -> 401/422
  - Forgot/reset password: generic response, valid reset changes password
  - Admin endpoints: 401 unauth, 403 wrong role, 200 for admin
  - Instructor applications: student can apply, admin can approve

## Files to Add/Modify (expected)
- Shared auth utils: `shared/educorp_common/auth/passwords.py`, `shared/educorp_common/auth/tokens.py`, update `shared/educorp_common/auth/dependencies.py`
- Auth models: `services/auth/app/models/*.py` + `__init__.py`
- Auth repositories: `services/auth/app/repositories/*.py` + `__init__.py`
- Auth services: `services/auth/app/services/*.py` + `__init__.py`
- Auth schemas: `services/auth/app/schemas/*.py` + `__init__.py`
- Auth routes: `services/auth/app/api/v1/auth.py`, `services/auth/app/api/v1/admin.py`, update router init
- Migration: `services/auth/alembic/versions/*_auth_phase1.py`
- Seed: `services/auth/scripts/seed.py` (+ `__init__.py`)
- Tests: `services/auth/tests/factories.py`, `services/auth/tests/unit/*.py`, `services/auth/tests/integration/*.py`
- Config: update [services/auth/app/config.py](services/auth/app/config.py)

## Verification
- Apply migration: `make migrate-service SERVICE=auth`
- Run auth tests: `make test-service SERVICE=auth`
- Manual checks (curl) for register/login/refresh/verify/me/admin endpoints per [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md)
- Ensure outbox rows are written in `auth.outbox` and audit entries in `auth.audit_log` for key actions
