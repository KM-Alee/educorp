from __future__ import annotations

import asyncio
import contextlib
import json

from aiokafka import AIOKafkaProducer
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.models.outbox import OutboxEvent
from educorp_common.outbox import OutboxRelay


class PublishingOutboxRelay:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._producer: AIOKafkaProducer | None = None
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await self._producer.start()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._producer is not None:
            await self._producer.stop()

    async def _run(self) -> None:
        assert self._producer is not None
        while not self._stopped.is_set():
            async with self._session_factory() as session:
                relay = OutboxRelay(session, OutboxEvent)
                published = await relay.publish_batch(
                    publisher=lambda event: self._publish(event),
                    batch_size=100,
                )
                await session.commit()
                if not published:
                    await asyncio.sleep(settings.relay_poll_interval_seconds)

    async def _publish(self, event) -> None:
        assert self._producer is not None
        await self._producer.send_and_wait(
            settings.course_lifecycle_topic,
            json.dumps(event.model_dump(mode="json")).encode("utf-8"),
        )
