from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """AI service settings."""

    service_name: str = "ai-service"
    service_port: int = 8006

    # Provider configuration
    llm_base_url: str = "https://nano-gpt.com/api/v1"
    llm_api_key: str = "change-me"
    llm_model: str = "google/gemma-4-31b-it"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2
    ai_provider_mode: str = "external"

    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = "change-me"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_timeout_seconds: int = 20

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "course_chunks_v2"

    # MongoDB
    mongo_url: str = "mongodb://educorp:educorp_dev@mongodb:27017/educorp?authSource=admin"
    mongo_db: str = "educorp"

    # Cache + rate limit
    ai_cache_ttl_seconds: int = 3600
    clarify_context_ttl_seconds: int = 900
    enrollment_cache_ttl_seconds: int = 900
    rate_limit_window_seconds: int = 60
    rate_limit_student_per_window: int = 20
    rate_limit_instructor_per_window: int = 5

    # Retrieval configuration
    retrieval_top_k: int = 12
    retrieval_candidate_pool: int = 64
    retrieval_full_scan_limit: int = 512
    relevance_threshold: float = 0.12
    min_chunks_for_answer: int = 1

    # Token budget
    max_input_tokens: int = 6000
    max_output_tokens: int = 1500
    max_context_chunks: int = 16

    # Kafka
    ai_usage_topic: str = "ai.usage"


settings = Settings()
