from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VersionArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "version_artifacts"
    __table_args__ = (
        Index("idx_version_artifacts_version", "version_id"),
        Index("idx_version_artifacts_type", "artifact_type"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    artifact_type: Mapped[str] = mapped_column(String(50))
    object_path: Mapped[str] = mapped_column(String(1000))
    sha256: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(String(100), default="application/json")
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    artifact_metadata: Mapped[dict] = mapped_column(JSONB, name="metadata", default=dict)
