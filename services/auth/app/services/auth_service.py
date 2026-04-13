from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.email_verification import EmailVerification
from app.models.password_reset import PasswordReset
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_role_repository import UserRoleRepository
from educorp_common.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from educorp_common.errors import (
    ConflictError,
    EduCorpError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)


class AuthService:
    """Authentication and user self-service workflows."""

    def __init__(self, session, redis: Redis) -> None:
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._user_roles = UserRoleRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._password_resets = PasswordResetRepository(session)
        self._email_verifications = EmailVerificationRepository(session)
        self._audit_logs = AuditLogRepository(session)
        self._outbox = OutboxRepository(session)
        self._redis = redis

    async def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered")

        student_role = await self._roles.get_by_name("student")
        if student_role is None:
            student_role = await self._roles.create(
                Role(name="student", description="Default student role")
            )

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_active=False,
            is_verified=False,
        )
        await self._users.create(user)

        await self._user_roles.add_role(user.id, student_role.id, granted_by=None)

        raw_token, token_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verification_ttl_hours
        )
        verification = EmailVerification(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self._email_verifications.create(verification)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.registered",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value={"email": user.email},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.created",
            data={"id": str(user.id), "email": user.email, "token": raw_token},
            metadata=self._event_metadata(correlation_id, user.id),
            correlation_id=self._parse_uuid(correlation_id),
        )

        return user

    async def verify_email(
        self,
        *,
        token: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        token_hash = hash_token(token)
        verification = await self._email_verifications.get_by_hash(token_hash)
        if verification is None:
            raise ValidationError("Invalid or expired token")
        if verification.verified_at is not None:
            return
        if verification.expires_at < datetime.now(timezone.utc):
            raise ValidationError("Invalid or expired token")

        user = await self._users.get_by_id(verification.user_id)
        if user is None:
            raise UnauthorizedError("Invalid token")

        verification.verified_at = datetime.now(timezone.utc)
        user.is_verified = True
        user.is_active = True
        await self._email_verifications.mark_verified(verification)
        await self._users.update(user)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.verified",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value={"is_verified": True},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.verified",
            data={"id": str(user.id), "email": user.email},
            metadata=self._event_metadata(correlation_id, user.id),
            correlation_id=self._parse_uuid(correlation_id),
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, int, User, list[str]]:
        await self._enforce_rate_limit(email=email, ip_address=ip_address)

        user = await self._users.get_by_email(email)
        if user is None:
            await self._record_failed_login(email, ip_address)
            raise UnauthorizedError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            await self._record_failed_login(email, ip_address)
            raise UnauthorizedError("Invalid credentials")

        if not user.is_active:
            raise ForbiddenError("Account is inactive")
        if not user.is_verified:
            raise ForbiddenError("Email is not verified")

        await self._clear_login_failures(email, ip_address)

        roles = await self._get_role_names(user.id)
        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
            roles=roles,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        )
        refresh_raw, refresh_hash = create_refresh_token()
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            device_info=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        await self._refresh_tokens.create(refresh_token)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.login",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value=None,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        expires_in = settings.jwt_access_token_expire_minutes * 60
        return access_token, refresh_raw, expires_in, user, roles

    async def refresh(
        self,
        *,
        refresh_token: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, int]:
        token_hash = hash_token(refresh_token)
        stored = await self._refresh_tokens.get_active_by_hash(token_hash)
        if stored is None:
            raise UnauthorizedError("Invalid refresh token")
        if stored.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token expired")

        user = await self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active or not user.is_verified:
            raise UnauthorizedError("Invalid refresh token")

        await self._refresh_tokens.revoke(stored)

        roles = await self._get_role_names(user.id)
        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
            roles=roles,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        )
        new_raw, new_hash = create_refresh_token()
        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            device_info=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        await self._refresh_tokens.create(new_refresh)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.refresh",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value=None,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        expires_in = settings.jwt_access_token_expire_minutes * 60
        return access_token, new_raw, expires_in

    async def forgot_password(
        self,
        *,
        email: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        user = await self._users.get_by_email(email)
        if user is None:
            return

        raw_token, token_hash = create_refresh_token()
        reset = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.password_reset_ttl_minutes),
        )
        await self._password_resets.create(reset)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.password_reset_requested",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value=None,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.password_reset_requested",
            data={"id": str(user.id), "email": user.email, "token": raw_token},
            metadata=self._event_metadata(correlation_id, user.id),
            correlation_id=self._parse_uuid(correlation_id),
        )

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        token_hash = hash_token(token)
        reset = await self._password_resets.get_by_hash(token_hash)
        if reset is None:
            raise ValidationError("Invalid or expired token")
        if reset.used_at is not None:
            raise ValidationError("Token already used")
        if reset.expires_at < datetime.now(timezone.utc):
            raise ValidationError("Invalid or expired token")

        user = await self._users.get_by_id(reset.user_id)
        if user is None:
            raise ValidationError("Invalid or expired token")

        user.password_hash = hash_password(new_password)
        await self._users.update(user)
        await self._password_resets.mark_used(reset)
        await self._refresh_tokens.revoke_all_for_user(user.id)

        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.password_reset",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value=None,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.password_reset",
            data={"id": str(user.id), "email": user.email},
            metadata=self._event_metadata(correlation_id, user.id),
            correlation_id=self._parse_uuid(correlation_id),
        )

    async def get_profile(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")
        return user

    async def update_profile(
        self,
        *,
        user_id: UUID,
        first_name: str | None,
        last_name: str | None,
        avatar_url: str | None,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if avatar_url is not None:
            user.avatar_url = avatar_url

        await self._users.update(user)
        await self._audit(
            actor_id=user.id,
            actor_type="user",
            action="user.profile_updated",
            resource_type="user",
            resource_id=user.id,
            old_value=None,
            new_value={"first_name": user.first_name, "last_name": user.last_name},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user

    async def _get_role_names(self, user_id: UUID) -> list[str]:
        role_ids = await self._user_roles.list_roles_for_user(user_id)
        roles = await self._roles.list_by_ids(role_ids)
        return [role.name for role in roles]

    async def _enforce_rate_limit(self, *, email: str, ip_address: str | None) -> None:
        ip_key = ip_address or "unknown"
        rate_key = f"auth:login:rate:{ip_key}"
        attempts = await self._redis.incr(rate_key)
        if attempts == 1:
            await self._redis.expire(rate_key, settings.login_rate_limit_window_seconds)
        if attempts > settings.login_rate_limit_max:
            raise EduCorpError(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many login attempts",
                status_code=429,
            )

        lock_key = f"auth:login:lock:{email}:{ip_key}"
        if await self._redis.exists(lock_key):
            raise ForbiddenError("Account locked. Try again later")

    async def _record_failed_login(self, email: str, ip_address: str | None) -> None:
        ip_key = ip_address or "unknown"
        fail_key = f"auth:login:fail:{email}:{ip_key}"
        failures = await self._redis.incr(fail_key)
        if failures == 1:
            await self._redis.expire(fail_key, settings.login_lockout_minutes * 60)
        if failures >= settings.login_lockout_threshold:
            lock_key = f"auth:login:lock:{email}:{ip_key}"
            await self._redis.set(lock_key, "1", ex=settings.login_lockout_minutes * 60)

    async def _clear_login_failures(self, email: str, ip_address: str | None) -> None:
        ip_key = ip_address or "unknown"
        await self._redis.delete(f"auth:login:fail:{email}:{ip_key}")
        await self._redis.delete(f"auth:login:lock:{email}:{ip_key}")

    async def _audit(
        self,
        *,
        actor_id: UUID | None,
        actor_type: str,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        old_value: dict | None,
        new_value: dict | None,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=self._parse_uuid(correlation_id),
        )
        return await self._audit_logs.create(entry)

    def _event_metadata(self, correlation_id: str, user_id: UUID) -> dict[str, Any]:
        return {
            "correlation_id": correlation_id,
            "source_service": "auth",
            "user_id": str(user_id),
        }

    def _parse_uuid(self, value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError:
            return uuid4()
