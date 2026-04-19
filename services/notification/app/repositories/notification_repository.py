from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    """Notification persistence helpers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_by_source_event(
        self,
        *,
        user_id: UUID,
        channel: str,
        source_event_id: str,
    ) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.channel == channel,
                Notification.source_event_id == source_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        is_read: bool | None,
        limit: int,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def mark_all_read(self, *, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=now, updated_at=now)
        )
        await self._session.flush()
        return int(result.rowcount or 0)
