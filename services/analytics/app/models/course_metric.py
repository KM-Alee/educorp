from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin


class CourseMetric(Base, TimestampMixin):
    """Per-course analytics materialization."""

    __tablename__ = "course_metrics"
    __table_args__ = ({"schema": "analytics"},)

    course_id: Mapped[UUID] = mapped_column(primary_key=True)
    instructor_id: Mapped[UUID | None] = mapped_column(default=None)
    course_title: Mapped[str | None] = mapped_column(String(300), default=None)
    total_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, default=0)
    ai_queries: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    latest_version_id: Mapped[UUID | None] = mapped_column(default=None)
