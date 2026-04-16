from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


class OutboxRepository:
    """Transactional outbox access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        data: dict,
        metadata: dict,
        correlation_id: UUID,
    ) -> OutboxEvent:
        payload = {
            "event_type": event_type,
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "metadata": metadata,
        }
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._session.add(event)
        await self._session.flush()
        return event