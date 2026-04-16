from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Enrollment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Student enrollment aggregate."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollments_student_course"),
        CheckConstraint(
            "status IN ('ENROLLED', 'CANCELLED', 'COMPLETED')",
            name="ck_enrollments_status",
        ),
        Index("idx_enrollments_student", "student_id"),
        Index("idx_enrollments_course", "course_id"),
        Index("idx_enrollments_status", "status"),
        Index(
            "idx_enrollments_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": "enrollment"},
    )

    student_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="ENROLLED")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), default=None)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)