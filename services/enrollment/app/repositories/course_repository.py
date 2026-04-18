from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class CourseEnrollmentMeta:
    course_id: UUID
    title: str
    max_capacity: int | None
    prerequisites: list[UUID]
    is_ready: bool


class CourseRepository:
    """Cross-schema course lookups for enrollment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_course_meta(self, course_id: UUID) -> CourseEnrollmentMeta | None:
        query = text(
            """
            SELECT c.id,
                   c.title,
                   c.max_capacity,
                   c.prerequisites,
                   c.visibility,
                   v.status,
                   v.activated_at
              FROM course.courses c
         LEFT JOIN publishing.course_versions v ON v.id = c.current_version_id
             WHERE c.id = :course_id
               AND c.deleted_at IS NULL
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        row = result.mappings().first()
        if row is None:
            return None

        prerequisites = [UUID(item) for item in (row.get("prerequisites") or [])]
        visibility = row.get("visibility")
        status = row.get("status")
        activated_at = row.get("activated_at")
        is_ready = (
            visibility == "PUBLISHED"
            and status == "READY"
            and activated_at is not None
        )
        return CourseEnrollmentMeta(
            course_id=UUID(str(row["id"])),
            title=str(row["title"]),
            max_capacity=row.get("max_capacity"),
            prerequisites=prerequisites,
            is_ready=is_ready,
        )

    async def list_required_module_ids(self, course_id: UUID) -> list[UUID]:
        query = text(
            """
            SELECT id
              FROM course.modules
             WHERE course_id = :course_id
               AND is_required = TRUE
             ORDER BY sort_order
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        return [UUID(str(row["id"])) for row in result.mappings().all()]
