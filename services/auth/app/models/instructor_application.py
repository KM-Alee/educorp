from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InstructorApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Instructor role application."""

    __tablename__ = "instructor_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="ck_instructor_app_status",
        ),
        {"schema": "auth"},
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth.users.id"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth.users.id"), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
