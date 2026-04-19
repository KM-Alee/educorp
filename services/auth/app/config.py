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


settings = Settings()
