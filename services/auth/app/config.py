from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Auth service settings."""

    service_name: str = "auth-service"
    service_port: int = 8001


settings = Settings()
