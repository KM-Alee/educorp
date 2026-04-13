from __future__ import annotations

from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.instructor_application_repository import InstructorApplicationRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_role_repository import UserRoleRepository

__all__ = [
    "AuditLogRepository",
    "EmailVerificationRepository",
    "InstructorApplicationRepository",
    "OutboxRepository",
    "PasswordResetRepository",
    "RefreshTokenRepository",
    "RoleRepository",
    "UserRepository",
    "UserRoleRepository",
]
