from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_progress import ModuleProgress


class ModuleProgressRepository:
    """Module progress data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_student_progress_and_module(
        self, student_progress_id: UUID, module_id: UUID
    ) -> ModuleProgress | None:
        result = await self._session.execute(
            select(ModuleProgress).where(
                ModuleProgress.student_progress_id == student_progress_id,
                ModuleProgress.module_id == module_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, progress: ModuleProgress) -> ModuleProgress:
        self._session.add(progress)
        await self._session.flush()
        return progress

    async def list_with_titles(self, student_progress_id: UUID) -> list[dict]:
        query = (
            select(
                ModuleProgress.module_id,
                ModuleProgress.module_title,
                ModuleProgress.sort_order,
                ModuleProgress.is_completed,
                ModuleProgress.progress_percent,
                ModuleProgress.completed_at,
            )
            .where(ModuleProgress.student_progress_id == student_progress_id)
            .order_by(ModuleProgress.sort_order)
        )
        result = await self._session.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def count_total(self, student_progress_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ModuleProgress)
            .where(
                ModuleProgress.student_progress_id == student_progress_id,
                ModuleProgress.is_required.is_(True),
            )
        )
        return int(result.scalar_one())

    async def count_completed(self, student_progress_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ModuleProgress)
            .where(
                ModuleProgress.student_progress_id == student_progress_id,
                ModuleProgress.is_required.is_(True),
                ModuleProgress.is_completed.is_(True),
            )
        )
        return int(result.scalar_one())
