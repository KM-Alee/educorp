from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment


class EnrollmentRepository:
    """Data access for enrollment records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, enrollment: Enrollment) -> Enrollment:
        self._session.add(enrollment)
        await self._session.flush()
        return enrollment

    async def update(self, enrollment: Enrollment) -> Enrollment:
        self._session.add(enrollment)
        await self._session.flush()
        return enrollment

    async def get_by_id(self, enrollment_id: UUID) -> Enrollment | None:
        result = await self._session.execute(
            select(Enrollment).where(Enrollment.id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_student_course(self, *, student_id: UUID, course_id: UUID) -> Enrollment | None:
        result = await self._session.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, *, idempotency_key: str) -> Enrollment | None:
        result = await self._session.execute(
            select(Enrollment).where(Enrollment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def list_for_student(
        self,
        *,
        student_id: UUID,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Enrollment], int]:
        query = select(Enrollment).where(Enrollment.student_id == student_id)
        if status:
            query = query.where(Enrollment.status == status)

        count_result = await self._session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = int(count_result.scalar_one())

        result = await self._session.execute(
            query.order_by(Enrollment.enrolled_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def count_active_for_course(self, *, course_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.status == "ENROLLED",
            )
        )
        return int(result.scalar_one())

    async def list_completed_course_ids(self, *, student_id: UUID, course_ids: list[UUID]) -> set[UUID]:
        if not course_ids:
            return set()
        result = await self._session.execute(
            select(Enrollment.course_id).where(
                Enrollment.student_id == student_id,
                Enrollment.status == "COMPLETED",
                Enrollment.course_id.in_(course_ids),
            )
        )
        return set(result.scalars().all())

    async def list_all(self) -> list[Enrollment]:
        result = await self._session.execute(select(Enrollment))
        return list(result.scalars().all())