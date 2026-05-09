from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings shared by all services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    service_name: str = "educorp-service"
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    metrics_enabled: bool = True
    traces_enabled: bool = True
    security_headers_enabled: bool = True

    # JWT
    jwt_secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "educorp"
    jwt_audience: str = "educorp-api"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://educorp:educorp_dev@postgres:5432/educorp"

    # Redis
    redis_url: str = "redis://:educorp_dev@redis:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_schema_registry_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KAFKA_SCHEMA_REGISTRY_URL",
            "SCHEMA_REGISTRY_URL",
        ),
        description="Confluent Schema Registry base URL; when set, lifecycle producers use JSON Schema encoding.",
    )

    # Observability
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"
    otel_service_name: str = "educorp"
    otel_traces_sampler: str = "always_on"
