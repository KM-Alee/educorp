from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

    async def get_by_workflow_id(self, workflow_id: str) -> CourseVersion | None:
        result = await self._session.execute(
            select(CourseVersion).where(CourseVersion.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_active_publishing_for_course(self, course_id: UUID) -> CourseVersion | None:
        result = await self._session.execute(
            select(CourseVersion).where(
                CourseVersion.course_id == course_id,
                CourseVersion.status.in_(["PREPARING", "REVIEW_REQUIRED", "PUBLISHING"]),
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

    async def list_workflows(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        course_id: UUID | None,
    ) -> tuple[list[CourseVersion], int]:
        filters = []
        if status:
            filters.append(CourseVersion.status == status)
        if course_id is not None:
            filters.append(CourseVersion.course_id == course_id)

        stmt = select(CourseVersion)
        count_stmt = select(func.count()).select_from(CourseVersion)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        stmt = (
            stmt.order_by(CourseVersion.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        total = await self._session.scalar(count_stmt)
        return list(result.scalars().all()), int(total or 0)

    async def get_active_version_id_for_course(
        self, course_id: UUID, *, exclude_version_id: UUID
    ) -> UUID | None:
        """Return the ID of any READY version (other than the given one) for a course."""
        result = await self._session.execute(
            select(CourseVersion.id).where(
                CourseVersion.course_id == course_id,
                CourseVersion.status == "READY",
                CourseVersion.activated_at.is_not(None),
                CourseVersion.id != exclude_version_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_superseded_before_retention(self, *, retention_days: int) -> list[CourseVersion]:
        """Return SUPERSEDED versions whose superseded_at is older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        result = await self._session.execute(
            select(CourseVersion).where(
                CourseVersion.status == "SUPERSEDED",
                CourseVersion.superseded_at <= cutoff,
            )
        )
        return list(result.scalars().all())
