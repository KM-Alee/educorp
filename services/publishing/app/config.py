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
    qdrant_collection: str = "course_chunks_v2"

    # Provider configuration
    nanogpt_base_url: str = "https://nano-gpt.com/api/v1"
    nanogpt_api_key: str = "change-me"
    nanogpt_model: str = "google/gemma-4-31b-it"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = "change-me"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Chunking — token-aware (1 token ≈ 4 chars)
    chunk_target_tokens: int = 500          # target chunk size in tokens
    chunk_max_tokens: int = 800             # hard cap in tokens
    chunk_overlap_tokens: int = 80          # overlap within same page
    chunk_size: int = 2000                  # legacy char-based fallback (unused by new chunker)
    chunk_overlap: int = 320               # legacy fallback
    embedding_batch_size: int = 64

    # Embedding cache TTL (seconds)
    embedding_cache_ttl_seconds: int = 604800  # 7 days

    # Cost guardrails for visual enrichment
    visual_enrichment_enabled: bool = True
    visual_enrichment_max_pages_per_asset: int = 10
    visual_enrichment_max_percent_per_asset: float = 0.20
    low_text_threshold_chars: int = 250
    ocr_confidence_threshold: float = 0.70
    visual_confidence_threshold: float = 0.65

    # Service-to-service
    course_service_url: str = "http://course-service:8000/api/v1"
    search_service_url: str = "http://search-service:8000/api/v1"
    internal_service_token: str = "change-me"

    # Cleanup retention
    superseded_vector_retention_days: int = 7


settings = Settings()
