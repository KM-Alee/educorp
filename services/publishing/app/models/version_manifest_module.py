from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VersionManifestModule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "version_manifest_modules"
    __table_args__ = (
        Index("idx_version_manifest_modules_version", "version_id"),
        Index("idx_version_manifest_modules_manifest", "manifest_id"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    manifest_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.version_manifests.id", ondelete="CASCADE")
    )
    module_id: Mapped[UUID] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_duration: Mapped[str | None] = mapped_column(String(32), default=None)
