from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


class UserRepository:
    """User data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(
                func.lower(User.email) == email.lower(), User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        query = select(User).where(User.deleted_at.is_(None))

        if search:
            like = f"%{search}%"
            query = query.where(
                or_(
                    User.email.ilike(like),
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                )
            )

        if is_active is not None:
            query = query.where(User.is_active.is_(is_active))

        if role:
            query = (
                query.join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.name == role)
            )
            query = query.distinct(User.id)

        count_subquery = query.subquery()
        total_result = await self._session.execute(
            select(func.count()).select_from(count_subquery)
        )
        total = int(total_result.scalar_one())

        query = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all()), total
