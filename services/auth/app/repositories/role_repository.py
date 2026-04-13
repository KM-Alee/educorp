from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role


class RoleRepository:
    """Role data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def list_by_names(self, names: list[str]) -> list[Role]:
        if not names:
            return []
        result = await self._session.execute(select(Role).where(Role.name.in_(names)))
        return list(result.scalars().all())

    async def list_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        if not role_ids:
            return []
        result = await self._session.execute(select(Role).where(Role.id.in_(role_ids)))
        return list(result.scalars().all())

    async def create(self, role: Role) -> Role:
        self._session.add(role)
        await self._session.flush()
        return role
