from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log entries for auth actions."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
        CheckConstraint(
            "actor_type IN ('user', 'system', 'admin')",
            name="ck_audit_actor_type",
        ),
        {"schema": "auth"},
    )

    actor_id: Mapped[UUID | None] = mapped_column(default=None)
    actor_type: Mapped[str] = mapped_column(String(20), default="user")
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[UUID | None] = mapped_column(default=None)
    old_value: Mapped[dict | None] = mapped_column(JSONB, default=None)
    new_value: Mapped[dict | None] = mapped_column(JSONB, default=None)
    ip_address: Mapped[str | None] = mapped_column(INET, default=None)
    user_agent: Mapped[str | None] = mapped_column(String(500), default=None)
    correlation_id: Mapped[UUID | None] = mapped_column(default=None)
