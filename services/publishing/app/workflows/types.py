from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PublishCourseInput:
    version_id: UUID


@dataclass(frozen=True)
class ArtifactActivityInput:
    version_id: UUID
    artifact_id: UUID


@dataclass(frozen=True)
class IndexArtifactsInput:
    version_id: UUID
    chunks_artifact_id: UUID
    embeddings_artifact_id: UUID


@dataclass(frozen=True)
class VersionFailureInput:
    version_id: UUID
    error_message: str
