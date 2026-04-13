from __future__ import annotations

from uuid import UUID, uuid4

from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_role_repository import UserRoleRepository
from educorp_common.errors import NotFoundError, ValidationError

ALLOWED_ROLES = {"student", "instructor", "admin"}


class AdminUserService:
    """Admin-level user management."""

    def __init__(self, session) -> None:
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._user_roles = UserRoleRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._audit_logs = AuditLogRepository(session)
        self._outbox = OutboxRepository(session)

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        role: str | None,
        is_active: bool | None,
        search: str | None,
    ) -> tuple[list[User], int]:
        return await self._users.list_users(
            page=page, page_size=page_size, role=role, is_active=is_active, search=search
        )

    async def get_role_names(self, user_id: UUID) -> list[str]:
        role_ids = await self._user_roles.list_roles_for_user(user_id)
        roles = await self._roles.list_by_ids(role_ids)
        return [role.name for role in roles]

    async def update_roles(
        self,
        *,
        user_id: UUID,
        add_roles: list[str],
        remove_roles: list[str],
        admin_id: UUID,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        invalid = [role for role in add_roles + remove_roles if role not in ALLOWED_ROLES]
        if invalid:
            raise ValidationError("Invalid role", details=[{"roles": invalid}])

        role_names = list({*add_roles, *remove_roles})
        roles = await self._roles.list_by_names(role_names)
        found = {role.name for role in roles}
        missing = [name for name in role_names if name not in found]
        if missing:
            raise ValidationError("Role not found", details=[{"roles": missing}])

        role_map = {role.name: role for role in roles}
        for role_name in add_roles:
            await self._user_roles.add_role(user_id, role_map[role_name].id, granted_by=admin_id)

        for role_name in remove_roles:
            await self._user_roles.remove_role(user_id, role_map[role_name].id)

        await self._refresh_tokens.revoke_all_for_user(user_id)

        await self._audit(
            actor_id=admin_id,
            actor_type="admin",
            action="user.roles_updated",
            resource_type="user",
            resource_id=user_id,
            old_value=None,
            new_value={"add_roles": add_roles, "remove_roles": remove_roles},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user_id,
            event_type="user.role_changed",
            data={"id": str(user_id), "roles": add_roles},
            metadata=self._event_metadata(correlation_id, user_id),
            correlation_id=self._parse_uuid(correlation_id),
        )

    async def update_status(
        self,
        *,
        user_id: UUID,
        is_active: bool,
        admin_id: UUID,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        user.is_active = is_active
        await self._users.update(user)
        if not is_active:
            await self._refresh_tokens.revoke_all_for_user(user_id)

        await self._audit(
            actor_id=admin_id,
            actor_type="admin",
            action="user.status_updated",
            resource_type="user",
            resource_id=user_id,
            old_value=None,
            new_value={"is_active": is_active},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="user",
            aggregate_id=user_id,
            event_type="user.status_changed",
            data={"id": str(user_id), "is_active": is_active},
            metadata=self._event_metadata(correlation_id, user_id),
            correlation_id=self._parse_uuid(correlation_id),
        )

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

    def _event_metadata(self, correlation_id: str, user_id: UUID) -> dict[str, str]:
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
