from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin


class DailyMetric(Base, TimestampMixin):
    """Daily platform analytics materialization."""

    __tablename__ = "daily_metrics"
    __table_args__ = ({"schema": "analytics"},)

    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_students: Mapped[int] = mapped_column(Integer, default=0)
    enrollments: Mapped[int] = mapped_column(Integer, default=0)
    completions: Mapped[int] = mapped_column(Integer, default=0)
    ai_queries: Mapped[int] = mapped_column(Integer, default=0)
    published_courses: Mapped[int] = mapped_column(Integer, default=0)
