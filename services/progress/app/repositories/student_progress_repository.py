from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_progress import StudentProgress


class StudentProgressRepository:
    """Data access for course progress records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, progress: StudentProgress) -> StudentProgress:
        self._session.add(progress)
        await self._session.flush()
        return progress

    async def update(self, progress: StudentProgress) -> StudentProgress:
        self._session.add(progress)
        await self._session.flush()
        return progress

    async def get_by_enrollment_id(self, *, enrollment_id: UUID) -> StudentProgress | None:
        result = await self._session.execute(
            select(StudentProgress).where(StudentProgress.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def list_for_student(self, *, student_id: UUID) -> list[StudentProgress]:
        result = await self._session.execute(
            select(StudentProgress)
            .where(StudentProgress.student_id == student_id)
            .order_by(StudentProgress.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_status(self, *, student_id: UUID, status: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(StudentProgress).where(
                StudentProgress.student_id == student_id,
                StudentProgress.status == status,
            )
        )
        return int(result.scalar_one())