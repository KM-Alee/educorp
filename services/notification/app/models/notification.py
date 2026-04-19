from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """In-app notification stored for a user."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", "source_event_id", name="uq_notifications_event"),
        Index("idx_notifications_user_created", "user_id", "created_at"),
        Index("idx_notifications_user_read", "user_id", "is_read"),
        {"schema": "notification"},
    )

    user_id: Mapped[UUID] = mapped_column()
    type: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(String(2000))
    source_event_id: Mapped[str | None] = mapped_column(String(100), default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    notification_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
