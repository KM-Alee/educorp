from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VersionManifestAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "version_manifest_assets"
    __table_args__ = (
        Index("idx_version_manifest_assets_version", "version_id"),
        Index("idx_version_manifest_assets_manifest", "manifest_id"),
        Index("idx_version_manifest_assets_module", "manifest_module_id"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    manifest_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.version_manifests.id", ondelete="CASCADE")
    )
    manifest_module_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.version_manifest_modules.id", ondelete="CASCADE")
    )
    asset_id: Mapped[UUID] = mapped_column()
    module_id: Mapped[UUID] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    asset_type: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(1000))
    checksum: Mapped[str] = mapped_column(String(128))
    sort_order: Mapped[int] = mapped_column(Integer)
    page_estimate: Mapped[int | None] = mapped_column(Integer, default=None)
