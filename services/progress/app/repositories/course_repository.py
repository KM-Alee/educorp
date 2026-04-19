from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CourseRepository:
    """Cross-schema course lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_course_title(self, course_id: UUID) -> str | None:
        result = await self._session.execute(
            text(
                """
                SELECT title
                  FROM course.courses
                 WHERE id = :course_id
                   AND deleted_at IS NULL
                """
            ),
            {"course_id": str(course_id)},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return str(row["title"])
