from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment_audit import EnrollmentAudit


class EnrollmentAuditRepository:
    """Enrollment audit access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: EnrollmentAudit) -> EnrollmentAudit:
        self._session.add(entry)
        await self._session.flush()
        return entry
