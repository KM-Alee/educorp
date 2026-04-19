from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
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

    async def list_entries(
        self,
        *,
        page: int,
        page_size: int,
        actor_id: UUID | None,
        action: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[list[EnrollmentAudit], int]:
        filters = []
        if actor_id is not None:
            filters.append(EnrollmentAudit.actor_id == actor_id)
        if action:
            filters.append(EnrollmentAudit.action == action)
        if from_date is not None:
            filters.append(EnrollmentAudit.created_at >= from_date)
        if to_date is not None:
            filters.append(EnrollmentAudit.created_at <= to_date)

        stmt = select(EnrollmentAudit)
        count_stmt = select(func.count()).select_from(EnrollmentAudit)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        stmt = (
            stmt.order_by(EnrollmentAudit.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        total = await self._session.scalar(count_stmt)
        return list(result.scalars().all()), int(total or 0)
