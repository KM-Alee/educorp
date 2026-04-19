from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EntitlementRepository:
    """Read-only cross-schema checks for AI access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_ready_course_version(self, course_id: UUID) -> tuple[UUID | None, str | None]:
        # Gate on visibility + activated_at only.  We intentionally omit
        # v.status = 'READY' because mark_version_failed can overwrite that
        # field even after activation succeeds (e.g. when notify_search_activated
        # fails after the course was already made live).  The canonical "is this
        # version live?" signal is activated_at IS NOT NULL.
        query = text(
            """
            SELECT c.current_version_id, c.title
              FROM course.courses c
              JOIN publishing.course_versions v ON v.id = c.current_version_id
             WHERE c.id = :course_id
               AND c.visibility = 'PUBLISHED'
               AND v.activated_at IS NOT NULL
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        row = result.first()
        if not row:
            return None, None
        return row[0], row[1]

    async def is_enrolled(self, student_id: UUID, course_id: UUID) -> bool:
        query = text(
            """
            SELECT 1
              FROM enrollment.enrollments e
             WHERE e.student_id = :student_id
               AND e.course_id = :course_id
               AND e.status IN ('ENROLLED', 'COMPLETED')
             LIMIT 1
            """
        )
        result = await self._session.execute(
            query, {"student_id": str(student_id), "course_id": str(course_id)}
        )
        return result.scalar_one_or_none() is not None

    async def is_course_owner(self, instructor_id: UUID, course_id: UUID) -> bool:
        query = text(
            """
            SELECT 1
              FROM course.courses c
             WHERE c.id = :course_id
               AND c.instructor_id = :instructor_id
               AND c.deleted_at IS NULL
             LIMIT 1
            """
        )
        result = await self._session.execute(
            query, {"course_id": str(course_id), "instructor_id": str(instructor_id)}
        )
        return result.scalar_one_or_none() is not None
