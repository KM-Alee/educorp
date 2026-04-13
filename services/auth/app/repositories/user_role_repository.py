from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_role import UserRole


class UserRoleRepository:
    """User-role association access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_role(self, user_id: UUID, role_id: UUID, granted_by: UUID | None) -> None:
        exists = await self._session.execute(
            select(UserRole.id).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        if exists.scalar_one_or_none() is not None:
            return

        user_role = UserRole(user_id=user_id, role_id=role_id, granted_by=granted_by)
        self._session.add(user_role)
        await self._session.flush()

    async def remove_role(self, user_id: UUID, role_id: UUID) -> None:
        result = await self._session.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        await self._session.delete(row)

    async def list_roles_for_user(self, user_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())
