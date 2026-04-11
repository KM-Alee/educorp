from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Course service settings."""

    service_name: str = "course-service"
    service_port: int = 8002


settings = Settings()
