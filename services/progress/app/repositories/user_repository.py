from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    """Cross-schema user lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_full_name(self, user_id: UUID) -> str | None:
        result = await self._session.execute(
            text(
                """
                                SELECT first_name, last_name
                                    FROM auth.users
                                 WHERE id = :user_id
                                     AND deleted_at IS NULL
                """
            ),
            {"user_id": str(user_id)},
        )
        row = result.mappings().first()
        if row is None:
            return None
        first = row.get("first_name") or ""
        last = row.get("last_name") or ""
        name = f"{first} {last}".strip()
        return name or None
