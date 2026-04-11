from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """AI service settings."""

    service_name: str = "ai-service"
    service_port: int = 8006


settings = Settings()
