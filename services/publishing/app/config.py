from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Publishing service settings."""

    service_name: str = "publishing-service"
    service_port: int = 8005


settings = Settings()
