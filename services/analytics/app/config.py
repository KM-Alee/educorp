from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Analytics service settings."""

    service_name: str = "analytics-service"
    service_port: int = 8009
    internal_service_token: str = "change-me"
    analytics_consumer_group: str = "analytics-service"
    consumer_max_retries: int = 3
    user_lifecycle_topic: str = "user.lifecycle"
    course_lifecycle_topic: str = "course.lifecycle"
    enrollment_lifecycle_topic: str = "enrollment.lifecycle"
    progress_lifecycle_topic: str = "progress.lifecycle"
    ai_usage_topic: str = "ai.usage"


settings = Settings()
