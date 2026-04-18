from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModuleProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Module-level progress for a student enrollment."""

    __tablename__ = "module_progress"
    __table_args__ = (
        UniqueConstraint("student_progress_id", "module_id", name="uq_module_progress_module"),
        Index("idx_module_progress_parent", "student_progress_id"),
        {"schema": "progress"},
    )

    student_progress_id: Mapped[UUID] = mapped_column(
        ForeignKey("progress.student_progress.id", ondelete="CASCADE")
    )
    module_id: Mapped[UUID] = mapped_column()
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
