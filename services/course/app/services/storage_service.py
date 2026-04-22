from __future__ import annotations

import hashlib
import io
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import structlog
from miniopy_async import Minio

from app.config import settings
from educorp_common.errors import ValidationError

logger = structlog.get_logger()

# Mapping of file extensions to expected MIME types
ALLOWED_TYPES: dict[str, list[str]] = {
    "pdf": ["application/pdf"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    "pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
    "txt": ["text/plain"],
    "md": ["text/markdown", "text/plain"],
    "vtt": ["text/vtt", "text/plain"],
    "srt": ["text/plain", "application/x-subrip"],
}

# Magic bytes for binary formats
MAGIC_BYTES: dict[str, bytes] = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",
    "pptx": b"PK\x03\x04",
}


def validate_file_type(file_name: str, content_type: str, header: bytes) -> str | None:
    """Validate file extension, MIME type, and magic bytes. Returns asset_type or None."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_TYPES:
        return None

    allowed_mimes = ALLOWED_TYPES[ext]
    if content_type not in allowed_mimes:
        return None

    if ext in MAGIC_BYTES and not header.startswith(MAGIC_BYTES[ext]):
        return None

    return ext


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of file data."""
    return hashlib.sha256(data).hexdigest()


def build_storage_path(
    course_id: UUID, module_id: UUID, asset_id: UUID, file_name: str
) -> str:
    """Build deterministic MinIO storage path."""
    safe_name = file_name.replace("/", "_").replace("\\", "_").replace("..", "")
    return f"course-assets/{course_id}/{module_id}/{asset_id}/{safe_name}"


class StorageService:
    """MinIO object-storage adapter."""

    def __init__(self, client: Minio) -> None:
        self._client = client
        self._bucket = settings.minio_bucket

    @staticmethod
    def validate_file(file_name: str, content_type: str, data: bytes) -> tuple[str, str]:
        header = data[:8]
        asset_type = validate_file_type(file_name, content_type, header)
        if asset_type is None:
            raise ValidationError("Unsupported file type")
        return asset_type, content_type

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        return compute_checksum(data)

    @staticmethod
    def storage_path(
        course_id: UUID, module_id: UUID, asset_id: UUID, file_name: str
    ) -> str:
        return build_storage_path(course_id, module_id, asset_id, file_name)

    async def upload(self, storage_path: str, data: bytes, content_type: str) -> None:
        await self._client.put_object(
            self._bucket,
            storage_path,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def presigned_url(self, storage_path: str, *, public: bool = True) -> str:
        from datetime import timedelta

        url = await self._client.presigned_get_object(
            self._bucket,
            storage_path,
            expires=timedelta(seconds=settings.presigned_url_ttl_seconds),
        )
        if not public:
            return url
        return self._rewrite_public_url(url)

    @staticmethod
    def _rewrite_public_url(url: str) -> str:
        parts = urlsplit(url)
        public_endpoint = settings.minio_public_endpoint.strip()

        if not public_endpoint or parts.netloc == public_endpoint:
            return url

        scheme = "https" if settings.minio_public_use_ssl else "http"
        return urlunsplit((scheme, public_endpoint, parts.path, parts.query, parts.fragment))

    async def delete(self, storage_path: str) -> None:
        try:
            await self._client.remove_object(self._bucket, storage_path)
        except Exception:
            logger.warning("Failed to delete object from storage", path=storage_path)
