from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PublishingStep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Step-level publishing progress tracking."""

    __tablename__ = "publishing_steps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_publishing_steps_status",
        ),
        Index("idx_pub_steps_version", "version_id"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    step_name: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    step_metadata: Mapped[dict] = mapped_column(JSONB, name="metadata", default=dict)
