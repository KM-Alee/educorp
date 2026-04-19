from __future__ import annotations

import asyncio
import contextlib
import json

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.models.dead_letter_message import DeadLetterMessage
from app.repositories.dead_letter_repository import DeadLetterRepository
from app.services.analytics_service import AnalyticsService
from educorp_common.events import DomainEvent, normalize_event
from educorp_common.telemetry import record_domain_event

logger = structlog.get_logger()


class AnalyticsKafkaConsumer:
    """Kafka consumer that materializes analytics from domain events."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            settings.user_lifecycle_topic,
            settings.course_lifecycle_topic,
            settings.enrollment_lifecycle_topic,
            settings.progress_lifecycle_topic,
            settings.ai_usage_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.analytics_consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._run())
        logger.info("Analytics Kafka consumer started")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._consumer is not None:
            await self._consumer.stop()
        logger.info("Analytics Kafka consumer stopped")

    async def _run(self) -> None:
        assert self._consumer is not None
        try:
            while not self._stopped.is_set():
                batch = await self._consumer.getmany(timeout_ms=1000, max_records=100)
                for topic_partition, records in batch.items():
                    for record in records:
                        event = normalize_event(dict(record.value))
                        await self._handle_event(
                            event,
                            topic=topic_partition.topic,
                            partition=record.partition,
                            offset=record.offset,
                            raw_message=dict(record.value),
                        )
                if batch:
                    await self._consumer.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Analytics Kafka consumer failed")
            raise

    async def _handle_event(
        self,
        event: DomainEvent,
        *,
        topic: str,
        partition: int,
        offset: int,
        raw_message: dict,
    ) -> None:
        for attempt in range(1, settings.consumer_max_retries + 1):
            async with self._session_factory() as session:
                service = AnalyticsService(session)
                try:
                    await service.ingest_events([event])
                    await session.commit()
                    record_domain_event(
                        service=settings.service_name,
                        event_type=event.event_type,
                        outcome="processed",
                    )
                    return
                except Exception as exc:
                    await session.rollback()
                    if attempt >= settings.consumer_max_retries:
                        repo = DeadLetterRepository(session)
                        await repo.create(
                            DeadLetterMessage(
                                topic=topic,
                                partition=partition,
                                offset=offset,
                                event_type=event.event_type,
                                error_message=str(exc),
                                retry_count=attempt,
                                raw_message=raw_message,
                            )
                        )
                        await session.commit()
                        record_domain_event(
                            service=settings.service_name,
                            event_type=event.event_type,
                            outcome="dead_lettered",
                        )
                        logger.warning(
                            "Analytics event moved to dead letter queue",
                            topic=topic,
                            partition=partition,
                            offset=offset,
                            event_type=event.event_type,
                        )
                        return
                    await asyncio.sleep(min(attempt, 3))
