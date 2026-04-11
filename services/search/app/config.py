from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Search service settings."""

    service_name: str = "search-service"
    service_port: int = 8007


settings = Settings()
