from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models.audit_log import AuditLog
from app.models.instructor_application import InstructorApplication
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.instructor_application_repository import InstructorApplicationRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_role_repository import UserRoleRepository
from educorp_common.errors import ConflictError, NotFoundError, ValidationError

ALLOWED_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


class InstructorApplicationService:
    """Instructor application workflows."""

    def __init__(self, session) -> None:
        self._applications = InstructorApplicationRepository(session)
        self._roles = RoleRepository(session)
        self._user_roles = UserRoleRepository(session)
        self._audit_logs = AuditLogRepository(session)
        self._outbox = OutboxRepository(session)

    async def apply(
        self,
        *,
        user_id: UUID,
        reason: str | None,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
        auto_approve: bool,
    ) -> InstructorApplication:
        existing = await self._applications.get_pending_for_user(user_id)
        if existing is not None:
            raise ConflictError("Application already pending")

        application = InstructorApplication(user_id=user_id, reason=reason)
        if auto_approve:
            application.status = "APPROVED"
            application.reviewed_at = datetime.now(timezone.utc)

        await self._applications.create(application)

        if auto_approve:
            await self._grant_instructor(user_id, reviewer_id=None)

        await self._audit(
            actor_id=user_id,
            actor_type="user",
            action="instructor.application_created",
            resource_type="instructor_application",
            resource_id=application.id,
            old_value=None,
            new_value={"status": application.status},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="instructor_application",
            aggregate_id=application.id,
            event_type="user.instructor_application.submitted",
            data={"id": str(application.id), "user_id": str(user_id)},
            metadata=self._event_metadata(correlation_id, user_id),
            correlation_id=self._parse_uuid(correlation_id),
        )

        return application

    async def list_applications(
        self,
        *,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[InstructorApplication], int]:
        if status and status not in ALLOWED_STATUSES:
            raise ValidationError("Invalid status")
        return await self._applications.list_applications(
            status=status, page=page, page_size=page_size
        )

    async def review_application(
        self,
        *,
        application_id: UUID,
        status: str,
        reviewer_id: UUID,
        correlation_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> InstructorApplication:
        if status not in ALLOWED_STATUSES:
            raise ValidationError("Invalid status")

        application = await self._applications.get_by_id(application_id)
        if application is None:
            raise NotFoundError("Application not found")

        application.status = status
        application.reviewed_by = reviewer_id
        application.reviewed_at = datetime.now(timezone.utc)
        await self._applications.update(application)

        if status == "APPROVED":
            await self._grant_instructor(application.user_id, reviewer_id)

        await self._audit(
            actor_id=reviewer_id,
            actor_type="admin",
            action="instructor.application_reviewed",
            resource_type="instructor_application",
            resource_id=application.id,
            old_value=None,
            new_value={"status": status},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._outbox.write(
            aggregate_type="instructor_application",
            aggregate_id=application.id,
            event_type="user.instructor_application.reviewed",
            data={"id": str(application.id), "status": status},
            metadata=self._event_metadata(correlation_id, application.user_id),
            correlation_id=self._parse_uuid(correlation_id),
        )

        return application

    async def _grant_instructor(self, user_id: UUID, reviewer_id: UUID | None) -> None:
        role = await self._roles.get_by_name("instructor")
        if role is None:
            raise ValidationError("Instructor role not configured")
        await self._user_roles.add_role(user_id, role.id, granted_by=reviewer_id)

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
