from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_progress import StudentProgress


class StudentProgressRepository:
    """Student progress data access."""

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

    async def get_by_enrollment(self, enrollment_id: UUID) -> StudentProgress | None:
        result = await self._session.execute(
            select(StudentProgress).where(StudentProgress.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[StudentProgress]:
        result = await self._session.execute(
            select(StudentProgress).where(StudentProgress.student_id == student_id)
        )
        return list(result.scalars().all())
