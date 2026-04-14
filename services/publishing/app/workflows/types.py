from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PublishCourseInput:
    course_id: UUID
    version_id: UUID


@dataclass(frozen=True)
class CourseAssetInfo:
    asset_id: UUID
    module_id: UUID
    asset_type: str
    file_name: str
    storage_path: str


@dataclass(frozen=True)
class ExtractedAsset:
    asset_id: UUID
    module_id: UUID
    asset_type: str
    text: str


@dataclass(frozen=True)
class ChunkPayload:
    chunk_id: UUID
    version_id: UUID
    course_id: UUID
    module_id: UUID
    asset_id: UUID
    chunk_index: int
    text: str
    char_start: int | None
    char_end: int | None
    token_count: int | None
    text_preview: str | None
