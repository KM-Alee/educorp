from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModuleProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-module progress state for a course enrollment."""

    __tablename__ = "module_progress"
    __table_args__ = (
        UniqueConstraint("student_progress_id", "module_id", name="uq_module_progress_parent_module"),
        Index("idx_module_progress_parent", "student_progress_id"),
        {"schema": "progress"},
    )

    student_progress_id: Mapped[UUID] = mapped_column(
        ForeignKey("progress.student_progress.id", ondelete="CASCADE")
    )
    module_id: Mapped[UUID]
    module_title: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int]
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)