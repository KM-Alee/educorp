from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin


class NotificationPreference(Base, TimestampMixin):
    """Per-user notification preferences for Phase 6 events."""

    __tablename__ = "notification_preferences"
    __table_args__ = ({"schema": "notification"},)

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    enrollment_confirmed_in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    enrollment_confirmed_email: Mapped[bool] = mapped_column(Boolean, default=True)
    course_completed_in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    course_completed_email: Mapped[bool] = mapped_column(Boolean, default=True)
    course_published_in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    course_published_email: Mapped[bool] = mapped_column(Boolean, default=True)
