from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Analytics service settings."""

    service_name: str = "analytics-service"
    service_port: int = 8009


settings = Settings()
