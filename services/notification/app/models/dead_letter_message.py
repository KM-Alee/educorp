from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeadLetterMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted failed consumer messages for admin inspection and replay."""

    __tablename__ = "dead_letter_messages"
    __table_args__ = (
        Index("idx_dead_letter_topic_created", "topic", "created_at"),
        Index("idx_dead_letter_replayed", "replayed_at"),
        {"schema": "notification"},
    )

    topic: Mapped[str] = mapped_column(String(100))
    partition: Mapped[int] = mapped_column(Integer)
    offset: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str | None] = mapped_column(String(100), default=None)
    error_message: Mapped[str] = mapped_column(String(1000))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_message: Mapped[dict] = mapped_column(JSONB, default=dict)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
