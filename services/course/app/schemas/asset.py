from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssetOut(BaseModel):
    """Asset response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    module_id: UUID
    title: str
    asset_type: str
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    checksum: str | None
    sort_order: int
    upload_status: str
    created_at: datetime
    updated_at: datetime


class AssetDownload(BaseModel):
    """Presigned download URL response."""

    download_url: str
    expires_in: int
