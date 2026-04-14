from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Search service settings."""

    service_name: str = "search-service"
    service_port: int = 8007

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "course_chunks"

    # Embeddings
    embedding_base_url: str = "https://nano-gpt.com/api/v1"
    embedding_api_key: str = "change-me"
    embedding_model: str = "text-embedding-ada-002"


settings = Settings()
