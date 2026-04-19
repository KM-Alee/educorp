from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Notification service settings."""

    service_name: str = "notification-service"
    service_port: int = 8008
    internal_service_token: str = "change-me"
    auth_service_url: str = "http://auth-service:8000/api/v1/auth"
    notification_from_email: str = "no-reply@educorp.local"
    notification_consumer_group: str = "notification-service"
    user_lifecycle_topic: str = "user.lifecycle"
    course_lifecycle_topic: str = "course.lifecycle"
    enrollment_lifecycle_topic: str = "enrollment.lifecycle"
    progress_lifecycle_topic: str = "progress.lifecycle"


settings = Settings()
