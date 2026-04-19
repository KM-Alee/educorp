from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter_message import DeadLetterMessage


class DeadLetterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: DeadLetterMessage) -> DeadLetterMessage:
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_id(self, message_id: UUID) -> DeadLetterMessage | None:
        result = await self._session.execute(
            select(DeadLetterMessage).where(DeadLetterMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_messages(
        self,
        *,
        page: int,
        page_size: int,
        topic: str | None,
    ) -> tuple[list[DeadLetterMessage], int]:
        filters = []
        if topic:
            filters.append(DeadLetterMessage.topic == topic)

        stmt = select(DeadLetterMessage)
        count_stmt = select(func.count()).select_from(DeadLetterMessage)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        stmt = (
            stmt.order_by(DeadLetterMessage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        total = await self._session.scalar(count_stmt)
        return list(result.scalars().all()), int(total or 0)

    async def mark_replayed(self, entry: DeadLetterMessage) -> DeadLetterMessage:
        entry.replayed_at = datetime.now(timezone.utc)
        self._session.add(entry)
        await self._session.flush()
        return entry
