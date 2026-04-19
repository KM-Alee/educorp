from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Auth service settings."""

    service_name: str = "auth-service"
    service_port: int = 8001

    password_min_length: int = 8
    login_rate_limit_max: int = 10
    login_rate_limit_window_seconds: int = 60
    login_lockout_threshold: int = 5
    login_lockout_minutes: int = 15
    email_verification_ttl_hours: int = 24
    password_reset_ttl_minutes: int = 60
    instructor_auto_approve: bool = False

    internal_service_token: str = "change-me"
    publishing_service_url: str = "http://publishing-service:8000/api/v1/publishing"
    notification_service_url: str = "http://notification-service:8000/api/v1/notifications"
    analytics_service_url: str = "http://analytics-service:8000/api/v1/analytics"
    enrollment_service_url: str = "http://enrollment-service:8000/api/v1/enrollments"
    user_lifecycle_topic: str = "user.lifecycle"
    relay_poll_interval_seconds: float = 2.0


settings = Settings()
