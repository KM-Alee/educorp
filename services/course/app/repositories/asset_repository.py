from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


class AssetRepository:
    """Data access for Asset entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, asset: Asset) -> Asset:
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        result = await self._session.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def list_for_module(self, module_id: UUID) -> list[Asset]:
        result = await self._session.execute(
            select(Asset)
            .where(Asset.module_id == module_id)
            .order_by(Asset.sort_order)
        )
        return list(result.scalars().all())

    async def update(self, asset: Asset) -> Asset:
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def delete(self, asset: Asset) -> None:
        await self._session.delete(asset)
        await self._session.flush()

    async def next_sort_order(self, module_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(Asset.sort_order), -1) + 1).where(
                Asset.module_id == module_id
            )
        )
        return int(result.scalar_one())

    async def count_for_module(self, module_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Asset).where(Asset.module_id == module_id)
        )
        return int(result.scalar_one())
