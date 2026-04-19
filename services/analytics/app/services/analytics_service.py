from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_store import EventStore
from app.repositories.course_metric_repository import CourseMetricRepository
from app.repositories.daily_metric_repository import DailyMetricRepository
from app.repositories.event_store_repository import EventStoreRepository
from app.schemas.analytics import CourseAnalyticsOut, PlatformAnalyticsOut
from educorp_common.errors import ForbiddenError, NotFoundError
from educorp_common.events import DomainEvent, DomainEventIngestResult


class AnalyticsService:
    """Phase 6 analytics ingestion and query logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventStoreRepository(session)
        self._daily = DailyMetricRepository(session)
        self._courses = CourseMetricRepository(session)

    async def ingest_events(self, events: list[DomainEvent]) -> DomainEventIngestResult:
        processed = 0
        skipped = 0
        for event in events:
            if await self._events.get_by_event_id(event.event_id):
                skipped += 1
                continue

            occurred_at = _parse_datetime(event.occurred_at)
            course_id = _uuid_or_none(event.payload.get("course_id"))
            await self._events.create(
                EventStore(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    actor_id=event.actor_id,
                    course_id=course_id,
                    source_service=event.source_service,
                    occurred_at=occurred_at,
                    event_payload=event.payload,
                    event_metadata=event.metadata,
                    raw_event=event.model_dump(mode="json"),
                    version=event.version,
                )
            )
            await self._materialize(event, occurred_at)
            processed += 1
        return DomainEventIngestResult(processed_count=processed, skipped_count=skipped)

    async def get_platform_metrics(
        self,
        *,
        from_date: date,
        to_date: date,
    ) -> PlatformAnalyticsOut:
        data = await self._daily.aggregate_range(from_date=from_date, to_date=to_date)
        return PlatformAnalyticsOut(from_date=from_date, to_date=to_date, **data)

    async def get_course_metrics(
        self,
        *,
        course_id: UUID,
        requester_id: UUID,
        roles: list[str],
    ) -> CourseAnalyticsOut:
        metric = await self._courses.get_by_course_id(course_id)
        if metric is None:
            raise NotFoundError("Course analytics not found")
        if (
            "admin" not in roles
            and metric.instructor_id is not None
            and metric.instructor_id != requester_id
        ):
            raise ForbiddenError("Access forbidden")
        return CourseAnalyticsOut(
            course_id=metric.course_id,
            instructor_id=metric.instructor_id,
            course_title=metric.course_title,
            total_enrollments=metric.total_enrollments,
            total_completions=metric.total_completions,
            completion_rate=float(metric.completion_rate or 0.0),
            ai_queries=metric.ai_queries,
            published_at=metric.published_at,
            latest_version_id=metric.latest_version_id,
        )

    async def _materialize(self, event: DomainEvent, occurred_at: datetime) -> None:
        daily = await self._daily.get_or_create(occurred_at.date())
        course_id = _uuid_or_none(event.payload.get("course_id"))
        course_metric = None if course_id is None else await self._courses.get_or_create(course_id)

        if event.event_type == "user.created":
            daily.total_students += 1
        elif event.event_type == "EnrollmentCreated":
            daily.enrollments += 1
            if course_metric is not None:
                course_metric.total_enrollments += 1
                course_metric.course_title = _coalesce_text(
                    event.payload.get("course_title"),
                    course_metric.course_title,
                )
        elif event.event_type == "CourseCompleted":
            daily.completions += 1
            if course_metric is not None:
                course_metric.total_completions += 1
                course_metric.course_title = _coalesce_text(
                    event.payload.get("course_title"),
                    course_metric.course_title,
                )
        elif event.event_type == "AssistantQueryAsked":
            daily.ai_queries += 1
            if course_metric is not None:
                course_metric.ai_queries += 1
        elif event.event_type in {"CoursePublished", "CourseReady"}:
            daily.published_courses += 1
            if course_metric is not None:
                course_metric.course_title = _coalesce_text(
                    event.payload.get("course_title"),
                    course_metric.course_title,
                )
                course_metric.instructor_id = (
                    _uuid_or_none(event.payload.get("instructor_id")) or course_metric.instructor_id
                )
                course_metric.latest_version_id = (
                    _uuid_or_none(event.payload.get("version_id"))
                    or course_metric.latest_version_id
                )
                course_metric.published_at = occurred_at

        if course_metric is not None:
            course_metric.completion_rate = _completion_rate(
                course_metric.total_completions,
                course_metric.total_enrollments,
            )
            await self._courses.update(course_metric)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _uuid_or_none(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _completion_rate(completions: int, enrollments: int) -> float:
    if enrollments <= 0:
        return 0.0
    return round((completions / enrollments) * 100.0, 2)


def _coalesce_text(value: object, fallback: str | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or fallback
