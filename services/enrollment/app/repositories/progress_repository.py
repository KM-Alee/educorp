from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ProgressRepository:
    """Cross-schema progress initialization and lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def initialize_progress(
        self,
        *,
        enrollment_id: UUID,
        student_id: UUID,
        course_id: UUID,
        module_ids: list[UUID],
    ) -> UUID:
        student_progress_id = uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO progress.student_progress (
                    id,
                    enrollment_id,
                    student_id,
                    course_id,
                    progress_percent,
                    status,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :enrollment_id,
                    :student_id,
                    :course_id,
                    :progress_percent,
                    :status,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": str(student_progress_id),
                "enrollment_id": str(enrollment_id),
                "student_id": str(student_id),
                "course_id": str(course_id),
                "progress_percent": 0.0,
                "status": "NOT_STARTED",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        )

        if module_ids:
            now = datetime.now(timezone.utc)
            values = [
                {
                    "id": str(uuid4()),
                    "student_progress_id": str(student_progress_id),
                    "module_id": str(module_id),
                    "is_completed": False,
                    "progress_percent": 0.0,
                    "created_at": now,
                    "updated_at": now,
                }
                for module_id in module_ids
            ]
            await self._session.execute(
                text(
                    """
                    INSERT INTO progress.module_progress (
                        id,
                        student_progress_id,
                        module_id,
                        is_completed,
                        progress_percent,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :student_progress_id,
                        :module_id,
                        :is_completed,
                        :progress_percent,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                values,
            )

        return student_progress_id

    async def get_progress_percent(self, enrollment_id: UUID) -> float | None:
        result = await self._session.execute(
            text(
                """
                SELECT progress_percent
                  FROM progress.student_progress
                 WHERE enrollment_id = :enrollment_id
                """
            ),
            {"enrollment_id": str(enrollment_id)},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return float(row["progress_percent"])
