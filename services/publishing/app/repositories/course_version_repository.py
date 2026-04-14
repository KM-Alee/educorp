from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_version import CourseVersion


class CourseVersionRepository:
    """Data access for course versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, version: CourseVersion) -> CourseVersion:
        self._session.add(version)
        await self._session.flush()
        return version

    async def get_by_id(self, version_id: UUID) -> CourseVersion | None:
        result = await self._session.execute(
            select(CourseVersion).where(CourseVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_active_publishing_for_course(
        self, course_id: UUID
    ) -> CourseVersion | None:
        result = await self._session.execute(
            select(CourseVersion).where(
                CourseVersion.course_id == course_id,
                CourseVersion.status == "PUBLISHING",
            )
        )
        return result.scalar_one_or_none()

    async def next_version_number(self, course_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(CourseVersion.version_number), 0) + 1).where(
                CourseVersion.course_id == course_id
            )
        )
        return int(result.scalar_one())

    async def update(self, version: CourseVersion) -> CourseVersion:
        self._session.add(version)
        await self._session.flush()
        return version

    async def set_run_id(self, version_id: UUID, run_id: str) -> CourseVersion | None:
        version = await self.get_by_id(version_id)
        if version is None:
            return None
        version.run_id = run_id
        return await self.update(version)
