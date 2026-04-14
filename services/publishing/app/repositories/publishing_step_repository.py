from __future__ import annotations

from uuid import UUID

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publishing_step import PublishingStep


class PublishingStepRepository:
    """Data access for publishing steps."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, steps: list[PublishingStep]) -> None:
        self._session.add_all(steps)
        await self._session.flush()

    async def update(self, step: PublishingStep) -> PublishingStep:
        self._session.add(step)
        await self._session.flush()
        return step

    async def get_by_version_and_name(
        self, version_id: UUID, step_name: str
    ) -> PublishingStep | None:
        result = await self._session.execute(
            select(PublishingStep).where(
                PublishingStep.version_id == version_id,
                PublishingStep.step_name == step_name,
            )
        )
        return result.scalar_one_or_none()

    async def reset_for_version(self, version_id: UUID) -> None:
        await self._session.execute(
            update(PublishingStep)
            .where(PublishingStep.version_id == version_id)
            .values(
                status="PENDING",
                started_at=None,
                completed_at=None,
                error_message=None,
                metadata={},
            )
        )
        await self._session.flush()

    async def mark_skipped_for_version(self, version_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(PublishingStep)
            .where(
                PublishingStep.version_id == version_id,
                PublishingStep.status.in_(["PENDING", "RUNNING"]),
            )
            .values(status="SKIPPED", completed_at=now)
        )
        await self._session.flush()

    async def list_for_version(self, version_id: UUID) -> list[PublishingStep]:
        result = await self._session.execute(
            select(PublishingStep)
            .where(PublishingStep.version_id == version_id)
            .order_by(PublishingStep.created_at)
        )
        return list(result.scalars().all())
