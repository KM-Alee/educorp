from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version_artifact import VersionArtifact


class VersionArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, artifact: VersionArtifact) -> VersionArtifact:
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def get_by_id(self, artifact_id: UUID) -> VersionArtifact | None:
        result = await self._session.execute(
            select(VersionArtifact).where(VersionArtifact.id == artifact_id)
        )
        return result.scalar_one_or_none()

    async def list_for_version(self, version_id: UUID) -> list[VersionArtifact]:
        result = await self._session.execute(
            select(VersionArtifact)
            .where(VersionArtifact.version_id == version_id)
            .order_by(VersionArtifact.created_at)
        )
        return list(result.scalars().all())

    async def find_by_type(
        self, version_id: UUID, artifact_type: str
    ) -> VersionArtifact | None:
        result = await self._session.execute(
            select(VersionArtifact)
            .where(
                VersionArtifact.version_id == version_id,
                VersionArtifact.artifact_type == artifact_type,
            )
            .order_by(VersionArtifact.created_at.desc())
        )
        return result.scalars().first()
