from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import Module


class ModuleRepository:
    """Data access for Module entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, module: Module) -> Module:
        self._session.add(module)
        await self._session.flush()
        return module

    async def get_by_id(self, module_id: UUID) -> Module | None:
        result = await self._session.execute(
            select(Module).where(Module.id == module_id)
        )
        return result.scalar_one_or_none()

    async def list_for_course(self, course_id: UUID) -> list[Module]:
        result = await self._session.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.sort_order)
        )
        return list(result.scalars().all())

    async def update(self, module: Module) -> Module:
        self._session.add(module)
        await self._session.flush()
        return module

    async def delete(self, module: Module) -> None:
        await self._session.delete(module)
        await self._session.flush()

    async def next_sort_order(self, course_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(Module.sort_order), -1) + 1).where(
                Module.course_id == course_id
            )
        )
        return int(result.scalar_one())

    async def reorder(self, course_id: UUID, ordered_ids: list[UUID]) -> None:
        for idx, module_id in enumerate(ordered_ids):
            await self._session.execute(
                update(Module)
                .where(Module.id == module_id, Module.course_id == course_id)
                .values(sort_order=idx)
            )
        await self._session.flush()

    async def count_for_course(self, course_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Module).where(Module.course_id == course_id)
        )
        return int(result.scalar_one())
