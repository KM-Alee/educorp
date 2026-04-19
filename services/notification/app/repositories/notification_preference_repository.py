from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import NotificationPreference


class NotificationPreferenceRepository:
    """Notification preference persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> NotificationPreference | None:
        result = await self._session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: UUID) -> NotificationPreference:
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing
        preference = NotificationPreference(user_id=user_id)
        self._session.add(preference)
        await self._session.flush()
        return preference

    async def update(self, preference: NotificationPreference) -> NotificationPreference:
        self._session.add(preference)
        await self._session.flush()
        return preference
