from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Publishing service settings."""

    service_name: str = "publishing-service"
    service_port: int = 8005

    # Temporal
    temporal_host: str = "temporal"
    temporal_port: int = 7233
    temporal_namespace: str = "educorp"
    temporal_task_queue: str = "publishing"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "educorp"
    minio_secret_key: str = "educorp_dev"
    minio_bucket: str = "course-assets"
    minio_use_ssl: bool = False

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "course_chunks"

    # Embeddings
    embedding_base_url: str = "https://nano-gpt.com/api/v1"
    embedding_api_key: str = "change-me"
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536

    # Chunking
    chunk_size: int = 1200
    chunk_overlap: int = 200
    embedding_batch_size: int = 64


settings = Settings()
