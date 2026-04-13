from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.course import Course


class Module(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Course module entity."""

    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("course_id", "sort_order", name="uq_modules_course_sort"),
        Index("idx_modules_course", "course_id"),
        {"schema": "course"},
    )

    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("course.courses.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_duration: Mapped[timedelta | None] = mapped_column(INTERVAL, default=None)

    # Relationships
    course: Mapped[Course] = relationship(back_populates="modules", lazy="raise")
    assets: Mapped[list[Asset]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Asset.sort_order",
    )
