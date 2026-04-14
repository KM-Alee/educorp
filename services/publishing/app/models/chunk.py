from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Chunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Relational reference for extracted content chunks."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_version", "version_id"),
        Index("idx_chunks_course", "course_id"),
        {"schema": "publishing"},
    )

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("publishing.course_versions.id", ondelete="CASCADE")
    )
    course_id: Mapped[UUID] = mapped_column()
    module_id: Mapped[UUID] = mapped_column()
    asset_id: Mapped[UUID] = mapped_column()
    chunk_index: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int | None] = mapped_column(Integer, default=None)
    char_end: Mapped[int | None] = mapped_column(Integer, default=None)
    token_count: Mapped[int | None] = mapped_column(Integer, default=None)
    text_preview: Mapped[str | None] = mapped_column(String(500), default=None)
