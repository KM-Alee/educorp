from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
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
        query = text(
            """
            SELECT mp.module_id,
                   mp.is_completed,
                   mp.progress_percent,
                   mp.completed_at,
                   m.title,
                   m.sort_order
              FROM progress.module_progress mp
              JOIN course.modules m ON m.id = mp.module_id
             WHERE mp.student_progress_id = :student_progress_id
             ORDER BY m.sort_order
            """
        )
        result = await self._session.execute(
            query, {"student_progress_id": str(student_progress_id)}
        )
        return [dict(row) for row in result.mappings().all()]

    async def count_total(self, student_progress_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(ModuleProgress).where(
                ModuleProgress.student_progress_id == student_progress_id
            )
        )
        return int(result.scalar_one())

    async def count_completed(self, student_progress_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(ModuleProgress).where(
                ModuleProgress.student_progress_id == student_progress_id,
                ModuleProgress.is_completed.is_(True),
            )
        )
        return int(result.scalar_one())
