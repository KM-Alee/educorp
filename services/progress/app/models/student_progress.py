from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudentProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Progress summary for a student enrollment."""

    __tablename__ = "student_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", name="uq_student_progress_enrollment"),
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_student_progress_status",
        ),
        Index("idx_student_progress_student", "student_id"),
        Index("idx_student_progress_course", "course_id"),
        {"schema": "progress"},
    )

    enrollment_id: Mapped[UUID] = mapped_column()
    student_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
