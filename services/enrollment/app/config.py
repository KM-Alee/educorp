from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Enrollment service settings."""

    service_name: str = "enrollment-service"
    service_port: int = 8003
    course_service_url: str = "http://course-service:8000/api/v1/courses"
    progress_service_url: str = "http://progress-service:8000/api/v1/progress"
    internal_service_token: str = "change-me"
    enrollment_lock_ttl_seconds: int = 30
    enrollment_status_cache_ttl_seconds: int = 900
    enrollment_idempotency_ttl_seconds: int = 900


settings = Settings()
