from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Enrollment service settings."""

    service_name: str = "enrollment-service"
    service_port: int = 8003


settings = Settings()
