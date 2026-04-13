from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course


class CourseRepository:
    """Data access for the Course aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, course: Course) -> Course:
        self._session.add(course)
        await self._session.flush()
        return course

    async def get_by_id(self, course_id: UUID) -> Course | None:
        result = await self._session.execute(
            select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Course | None:
        result = await self._session.execute(
            select(Course).where(Course.slug == slug, Course.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        query = select(func.count()).select_from(Course).where(
            Course.slug == slug, Course.deleted_at.is_(None)
        )
        if exclude_id is not None:
            query = query.where(Course.id != exclude_id)
        result = await self._session.execute(query)
        return int(result.scalar_one()) > 0

    async def update(self, course: Course) -> Course:
        self._session.add(course)
        await self._session.flush()
        return course

    async def soft_delete(self, course: Course) -> None:
        from datetime import datetime, timezone

        course.deleted_at = datetime.now(timezone.utc)
        self._session.add(course)
        await self._session.flush()

    async def list_courses(
        self,
        *,
        page: int,
        page_size: int,
        instructor_id: UUID | None = None,
        category: str | None = None,
        difficulty: str | None = None,
        visibility: str | None = None,
        search: str | None = None,
        include_drafts: bool = False,
    ) -> tuple[list[Course], int]:
        query = select(Course).where(Course.deleted_at.is_(None))

        if not include_drafts:
            query = query.where(Course.visibility == "PUBLISHED")

        if visibility:
            query = query.where(Course.visibility == visibility)
        if instructor_id:
            query = query.where(Course.instructor_id == instructor_id)
        if category:
            query = query.where(Course.category == category)
        if difficulty:
            query = query.where(Course.difficulty == difficulty)
        if search:
            like = f"%{search}%"
            query = query.where(Course.title.ilike(like) | Course.description.ilike(like))

        count_sub = query.subquery()
        total_result = await self._session.execute(
            select(func.count()).select_from(count_sub)
        )
        total = int(total_result.scalar_one())

        query = query.order_by(Course.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total
