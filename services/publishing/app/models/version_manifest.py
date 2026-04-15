from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VersionManifest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "version_manifests"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_version_manifests_version_id"),
        Index("idx_version_manifests_version", "version_id"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    course_id: Mapped[UUID] = mapped_column()
    instructor_id: Mapped[UUID] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    short_description: Mapped[str | None] = mapped_column(String(500), default=None)
    category: Mapped[str | None] = mapped_column(String(100), default=None)
    difficulty: Mapped[str | None] = mapped_column(String(20), default=None)
    estimated_duration: Mapped[str | None] = mapped_column(String(32), default=None)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
