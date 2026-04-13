from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """Course service settings."""

    service_name: str = "course-service"
    service_port: int = 8002

    # MongoDB
    mongo_url: str = "mongodb://educorp:educorp_dev@mongodb:27017/educorp?authSource=admin"
    mongo_db: str = "educorp"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "educorp"
    minio_secret_key: str = "educorp_dev"
    minio_bucket: str = "course-assets"
    minio_use_ssl: bool = False

    # Upload limits
    max_asset_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    presigned_url_ttl_seconds: int = 3600


settings = Settings()
