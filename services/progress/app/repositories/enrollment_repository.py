from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class EnrollmentRecord:
    enrollment_id: UUID
    student_id: UUID
    course_id: UUID
    status: str


class EnrollmentRepository:
    """Cross-schema enrollment lookups and updates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, enrollment_id: UUID) -> EnrollmentRecord | None:
        query = text(
            """
            SELECT id, student_id, course_id, status
              FROM enrollment.enrollments
             WHERE id = :enrollment_id
            """
        )
        result = await self._session.execute(
            query, {"enrollment_id": str(enrollment_id)}
        )
        row = result.mappings().first()
        if row is None:
            return None
        return EnrollmentRecord(
            enrollment_id=UUID(str(row["id"])),
            student_id=UUID(str(row["student_id"])),
            course_id=UUID(str(row["course_id"])),
            status=str(row["status"]),
        )

    async def mark_completed(self, enrollment_id: UUID) -> None:
        await self._session.execute(
            text(
                """
                UPDATE enrollment.enrollments
                   SET status = 'COMPLETED',
                       completed_at = :completed_at,
                       updated_at = :updated_at
                 WHERE id = :enrollment_id
                """
            ),
            {
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "enrollment_id": str(enrollment_id),
            },
        )
