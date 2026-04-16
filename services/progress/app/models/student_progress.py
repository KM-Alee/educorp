from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudentProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Progress record for a student's enrollment in a course."""

    __tablename__ = "student_progress"
    __table_args__ = (
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_student_progress_status",
        ),
        Index("idx_student_progress_student", "student_id"),
        Index("idx_student_progress_course", "course_id"),
        {"schema": "progress"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(unique=True)
    student_id: Mapped[UUID]
    course_id: Mapped[UUID]
    course_title: Mapped[str] = mapped_column(String(300))
    progress_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)