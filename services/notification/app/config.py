from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Notification service settings."""

    service_name: str = "notification-service"
    service_port: int = 8008


settings = Settings()
