from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment_audit import EnrollmentAudit


class EnrollmentAuditRepository:
    """Persistence for enrollment audit rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, audit_entry: EnrollmentAudit) -> EnrollmentAudit:
        self._session.add(audit_entry)
        await self._session.flush()
        return audit_entry