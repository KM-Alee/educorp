from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_metric import CourseMetric


class CourseMetricRepository:
    """Per-course materialized metrics persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_course_id(self, course_id: UUID) -> CourseMetric | None:
        result = await self._session.execute(
            select(CourseMetric).where(CourseMetric.course_id == course_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, course_id: UUID) -> CourseMetric:
        metric = await self.get_by_course_id(course_id)
        if metric is not None:
            return metric
        metric = CourseMetric(course_id=course_id)
        self._session.add(metric)
        await self._session.flush()
        return metric

    async def update(self, metric: CourseMetric) -> CourseMetric:
        self._session.add(metric)
        await self._session.flush()
        return metric
