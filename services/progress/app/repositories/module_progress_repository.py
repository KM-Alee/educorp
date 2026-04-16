from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_progress import ModuleProgress


class ModuleProgressRepository:
    """Data access for module progress records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, modules: list[ModuleProgress]) -> list[ModuleProgress]:
        self._session.add_all(modules)
        await self._session.flush()
        return modules

    async def update(self, module_progress: ModuleProgress) -> ModuleProgress:
        self._session.add(module_progress)
        await self._session.flush()
        return module_progress

    async def list_for_progress(self, *, student_progress_id: UUID) -> list[ModuleProgress]:
        result = await self._session.execute(
            select(ModuleProgress)
            .where(ModuleProgress.student_progress_id == student_progress_id)
            .order_by(ModuleProgress.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_by_progress_and_module(
        self,
        *,
        student_progress_id: UUID,
        module_id: UUID,
    ) -> ModuleProgress | None:
        result = await self._session.execute(
            select(ModuleProgress).where(
                ModuleProgress.student_progress_id == student_progress_id,
                ModuleProgress.module_id == module_id,
            )
        )
        return result.scalar_one_or_none()