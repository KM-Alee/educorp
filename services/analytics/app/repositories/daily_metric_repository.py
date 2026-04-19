from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_metric import DailyMetric


class DailyMetricRepository:
    """Daily metric persistence and aggregation queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, metric_date: date) -> DailyMetric:
        result = await self._session.execute(
            select(DailyMetric).where(DailyMetric.metric_date == metric_date)
        )
        metric = result.scalar_one_or_none()
        if metric is not None:
            return metric
        metric = DailyMetric(metric_date=metric_date)
        self._session.add(metric)
        await self._session.flush()
        return metric

    async def aggregate_range(self, *, from_date: date, to_date: date) -> dict[str, int]:
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(DailyMetric.total_students), 0),
                func.coalesce(func.sum(DailyMetric.enrollments), 0),
                func.coalesce(func.sum(DailyMetric.completions), 0),
                func.coalesce(func.sum(DailyMetric.ai_queries), 0),
                func.coalesce(func.sum(DailyMetric.published_courses), 0),
            ).where(DailyMetric.metric_date >= from_date, DailyMetric.metric_date <= to_date)
        )
        row = result.one()
        return {
            "total_students": int(row[0] or 0),
            "enrollments": int(row[1] or 0),
            "completions": int(row[2] or 0),
            "ai_usage": int(row[3] or 0),
            "published_courses": int(row[4] or 0),
        }
