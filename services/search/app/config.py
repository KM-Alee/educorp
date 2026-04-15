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
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = "change-me"
    openai_embedding_model: str = "text-embedding-3-small"


settings = Settings()
