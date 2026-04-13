from __future__ import annotations

from app.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession


class AuditLogRepository:
    """Audit log access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: AuditLog) -> AuditLog:
        self._session.add(entry)
        await self._session.flush()
        return entry
