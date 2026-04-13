from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerification


class EmailVerificationRepository:
    """Email verification token access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> EmailVerification | None:
        result = await self._session.execute(
            select(EmailVerification).where(EmailVerification.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def create(self, verification: EmailVerification) -> EmailVerification:
        self._session.add(verification)
        await self._session.flush()
        return verification

    async def mark_verified(self, verification: EmailVerification) -> None:
        verification.verified_at = datetime.now(timezone.utc)
        self._session.add(verification)
        await self._session.flush()
