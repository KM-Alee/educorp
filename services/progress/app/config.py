from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Progress service settings."""

    service_name: str = "progress-service"
    service_port: int = 8004
    internal_service_token: str = "change-me"
    enrollment_service_url: str = "http://enrollment-service:8000/api/v1"


settings = Settings()
