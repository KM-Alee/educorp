from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Progress service settings."""

    service_name: str = "progress-service"
    service_port: int = 8004


settings = Settings()
