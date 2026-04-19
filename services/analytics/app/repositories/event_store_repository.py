from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_store import EventStore


class EventStoreRepository:
    """Immutable event log persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_event_id(self, event_id: str) -> EventStore | None:
        result = await self._session.execute(
            select(EventStore).where(EventStore.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def create(self, event: EventStore) -> EventStore:
        self._session.add(event)
        await self._session.flush()
        return event
