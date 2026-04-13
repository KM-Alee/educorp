from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordReset


class PasswordResetRepository:
    """Password reset token access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> PasswordReset | None:
        result = await self._session.execute(
            select(PasswordReset).where(PasswordReset.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def create(self, reset: PasswordReset) -> PasswordReset:
        self._session.add(reset)
        await self._session.flush()
        return reset

    async def mark_used(self, reset: PasswordReset) -> None:
        reset.used_at = datetime.now(timezone.utc)
        self._session.add(reset)
        await self._session.flush()
