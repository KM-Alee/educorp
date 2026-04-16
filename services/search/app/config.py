from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Search service settings."""

    service_name: str = "search-service"
    service_port: int = 8007

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "course_chunks_v2"

    # Provider configuration
    nanogpt_base_url: str = "https://nano-gpt.com/api/v1"
    nanogpt_api_key: str = "change-me"
    nanogpt_model: str = "google/gemma-4-31b-it"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = "change-me"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Internal service-to-service auth
    internal_service_token: str = "change-me"


settings = Settings()
