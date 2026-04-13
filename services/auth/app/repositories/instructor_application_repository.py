from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instructor_application import InstructorApplication


class InstructorApplicationRepository:
    """Instructor application access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, application_id: UUID) -> InstructorApplication | None:
        result = await self._session.execute(
            select(InstructorApplication).where(InstructorApplication.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_for_user(self, user_id: UUID) -> InstructorApplication | None:
        result = await self._session.execute(
            select(InstructorApplication).where(
                InstructorApplication.user_id == user_id,
                InstructorApplication.status == "PENDING",
            )
        )
        return result.scalar_one_or_none()

    async def create(self, application: InstructorApplication) -> InstructorApplication:
        self._session.add(application)
        await self._session.flush()
        return application

    async def list_applications(
        self,
        *,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[InstructorApplication], int]:
        query = select(InstructorApplication)
        if status:
            query = query.where(InstructorApplication.status == status)

        count_subquery = query.subquery()
        total_result = await self._session.execute(
            select(func.count()).select_from(count_subquery)
        )
        total = int(total_result.scalar_one())

        query = query.order_by(InstructorApplication.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def update(self, application: InstructorApplication) -> InstructorApplication:
        self._session.add(application)
        await self._session.flush()
        return application
