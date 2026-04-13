from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, INTERVAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from educorp_common.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.module import Module


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Course aggregate root."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_courses_difficulty",
        ),
        CheckConstraint(
            "visibility IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name="ck_courses_visibility",
        ),
        Index("idx_courses_instructor", "instructor_id", postgresql_where="deleted_at IS NULL"),
        Index("idx_courses_visibility", "visibility", postgresql_where="deleted_at IS NULL"),
        Index("idx_courses_category", "category", postgresql_where="deleted_at IS NULL"),
        Index("idx_courses_slug", "slug"),
        Index("idx_courses_tags", "tags", postgresql_using="gin"),
        {"schema": "course"},
    )

    instructor_id: Mapped[UUID] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(300), unique=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    short_description: Mapped[str | None] = mapped_column(String(500), default=None)
    category: Mapped[str | None] = mapped_column(String(100), default=None)
    difficulty: Mapped[str | None] = mapped_column(String(20), default=None)
    estimated_duration: Mapped[timedelta | None] = mapped_column(INTERVAL, default=None)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), default=None)
    is_public_preview: Mapped[bool] = mapped_column(Boolean, default=False)
    max_capacity: Mapped[int | None] = mapped_column(Integer, default=None)
    prerequisites: Mapped[list[UUID]] = mapped_column(
        ARRAY(String), server_default="{}"
    )
    visibility: Mapped[str] = mapped_column(String(20), default="DRAFT")
    current_version_id: Mapped[UUID | None] = mapped_column(default=None)

    # Relationships (use string references to avoid circular imports)
    modules: Mapped[list[Module]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Module.sort_order",
    )
