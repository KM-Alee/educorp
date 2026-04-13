from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.module import Module


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Course asset (uploaded file) entity."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('pdf', 'docx', 'pptx', 'txt', 'md', 'vtt', 'srt')",
            name="ck_assets_type",
        ),
        CheckConstraint(
            "upload_status IN ('PENDING', 'UPLOADED', 'FAILED')",
            name="ck_assets_upload_status",
        ),
        Index("idx_assets_module", "module_id"),
        {"schema": "course"},
    )

    module_id: Mapped[UUID] = mapped_column(
        ForeignKey("course.modules.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(300))
    asset_type: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(1000))
    checksum: Mapped[str | None] = mapped_column(String(128), default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    upload_status: Mapped[str] = mapped_column(String(20), default="PENDING")

    # Relationships
    module: Mapped[Module] = relationship(back_populates="assets", lazy="raise")
