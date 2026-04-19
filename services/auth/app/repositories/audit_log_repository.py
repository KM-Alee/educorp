from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

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

    async def list_entries(
        self,
        *,
        page: int,
        page_size: int,
        actor_id: UUID | None,
        action: str | None,
        resource_type: str | None,
        resource_id: UUID | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)
        if action:
            filters.append(AuditLog.action == action)
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            filters.append(AuditLog.resource_id == resource_id)
        if from_date is not None:
            filters.append(AuditLog.created_at >= from_date)
        if to_date is not None:
            filters.append(AuditLog.created_at <= to_date)

        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        stmt = (
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        total = await self._session.scalar(count_stmt)
        return list(result.scalars().all()), int(total or 0)
