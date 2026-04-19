from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    """API representation of a notification."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: str
    channel: str
    title: str
    message: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    metadata: dict = Field(
        default_factory=dict,
        validation_alias="notification_metadata",
        serialization_alias="metadata",
    )


class NotificationPreferenceOut(BaseModel):
    """API representation of notification preferences."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    enrollment_confirmed_in_app: bool
    enrollment_confirmed_email: bool
    course_completed_in_app: bool
    course_completed_email: bool
    course_published_in_app: bool
    course_published_email: bool


class NotificationPreferenceUpdate(BaseModel):
    """Partial update payload for notification preferences."""

    enrollment_confirmed_in_app: bool | None = None
    enrollment_confirmed_email: bool | None = None
    course_completed_in_app: bool | None = None
    course_completed_email: bool | None = None
    course_published_in_app: bool | None = None
    course_published_email: bool | None = None


class NotificationReadAllOut(BaseModel):
    """Response payload after marking notifications as read."""

    updated_count: int
