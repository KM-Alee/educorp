from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, UUIDPrimaryKeyMixin


class EnrollmentAudit(Base, UUIDPrimaryKeyMixin):
    """Enrollment lifecycle audit row."""

    __tablename__ = "enrollment_audit"
    __table_args__ = (
        Index("idx_enrollment_audit_enrollment", "enrollment_id"),
        Index("idx_enrollment_audit_correlation", "correlation_id"),
        {"schema": "enrollment"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment.enrollments.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[UUID]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[UUID | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )