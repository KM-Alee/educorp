from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CourseVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Published course version metadata."""

    __tablename__ = "course_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHING', 'READY', 'FAILED', 'CANCELLED')",
            name="ck_course_versions_status",
        ),
        Index("idx_versions_course", "course_id"),
        Index("idx_versions_status", "status"),
        Index(
            "idx_one_publishing_per_course",
            "course_id",
            unique=True,
            postgresql_where=text("status = 'PUBLISHING'"),
        ),
        Index(
            "idx_versions_course_number",
            "course_id",
            "version_number",
            unique=True,
        ),
        {"schema": "publishing"},
    )

    course_id: Mapped[UUID] = mapped_column()
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHING")
    initiated_by: Mapped[UUID] = mapped_column()
    workflow_id: Mapped[str | None] = mapped_column(String(255), default=None)
    run_id: Mapped[str | None] = mapped_column(String(255), default=None)
    error_details: Mapped[dict | None] = mapped_column(JSONB, default=None)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_assets: Mapped[int] = mapped_column(Integer, default=0)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
