from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, UUIDPrimaryKeyMixin


class EnrollmentAudit(Base, UUIDPrimaryKeyMixin):
    """Audit log entries for enrollment actions."""

    __tablename__ = "enrollment_audit"
    __table_args__ = (
        Index("idx_enrollment_audit_enrollment", "enrollment_id"),
        Index("idx_enrollment_audit_correlation", "correlation_id"),
        {"schema": "enrollment"},
    )

    enrollment_id: Mapped[UUID] = mapped_column()
    action: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[UUID] = mapped_column()
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    correlation_id: Mapped[UUID | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
