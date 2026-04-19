from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventStore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable analytics event log."""

    __tablename__ = "event_store"
    __table_args__ = (
        Index("idx_event_store_event_id", "event_id", unique=True),
        Index("idx_event_store_type_time", "event_type", "occurred_at"),
        Index("idx_event_store_course", "course_id"),
        {"schema": "analytics"},
    )

    event_id: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_type: Mapped[str | None] = mapped_column(String(100), default=None)
    aggregate_id: Mapped[str | None] = mapped_column(String(100), default=None)
    actor_id: Mapped[str | None] = mapped_column(String(100), default=None)
    course_id: Mapped[UUID | None] = mapped_column(default=None)
    source_service: Mapped[str | None] = mapped_column(String(100), default=None)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_payload: Mapped[dict] = mapped_column("payload", JSONB, default=dict)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    raw_event: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
