from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version_manifest import VersionManifest
from app.models.version_manifest_asset import VersionManifestAsset
from app.models.version_manifest_module import VersionManifestModule


class VersionManifestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, manifest: VersionManifest) -> VersionManifest:
        self._session.add(manifest)
        await self._session.flush()
        return manifest

    async def create_modules(
        self, modules: list[VersionManifestModule]
    ) -> list[VersionManifestModule]:
        self._session.add_all(modules)
        await self._session.flush()
        return modules

    async def create_assets(
        self, assets: list[VersionManifestAsset]
    ) -> list[VersionManifestAsset]:
        self._session.add_all(assets)
        await self._session.flush()
        return assets

    async def get_by_version_id(self, version_id: UUID) -> VersionManifest | None:
        result = await self._session.execute(
            select(VersionManifest).where(VersionManifest.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_modules_for_version(self, version_id: UUID) -> list[VersionManifestModule]:
        result = await self._session.execute(
            select(VersionManifestModule)
            .where(VersionManifestModule.version_id == version_id)
            .order_by(VersionManifestModule.sort_order)
        )
        return list(result.scalars().all())

    async def list_assets_for_version(self, version_id: UUID) -> list[VersionManifestAsset]:
        result = await self._session.execute(
            select(VersionManifestAsset)
            .where(VersionManifestAsset.version_id == version_id)
            .order_by(VersionManifestAsset.sort_order)
        )
        return list(result.scalars().all())
