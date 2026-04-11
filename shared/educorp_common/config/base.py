from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings shared by all services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://educorp:educorp_dev@postgres:5432/educorp"

    # Redis
    redis_url: str = "redis://:educorp_dev@redis:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"
    otel_service_name: str = "educorp"
