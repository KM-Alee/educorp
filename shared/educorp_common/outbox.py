from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from educorp_common.events import DomainEvent, outbox_row_to_event

Publisher = Callable[[DomainEvent], Awaitable[None]]


class OutboxRelay:
    """Generic transactional outbox relay used by Phase 6 event pipelines."""

    def __init__(self, session: AsyncSession, model: type[Any]) -> None:
        self._session = session
        self._model = model

    async def publish_batch(
        self,
        *,
        publisher: Publisher,
        batch_size: int = 100,
    ) -> list[DomainEvent]:
        result = await self._session.execute(
            select(self._model)
            .where(self._model.published_at.is_(None))
            .order_by(self._model.created_at.asc())
            .limit(batch_size)
        )
        rows = list(result.scalars().all())
        published: list[DomainEvent] = []
        now = datetime.now(timezone.utc)
        for row in rows:
            event = outbox_row_to_event(row)
            await publisher(event)
            row.published_at = now
            self._session.add(row)
            published.append(event)
        await self._session.flush()
        return published
