from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CourseSearchRepository:
    """Catalog and metadata search queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_courses(
        self,
        *,
        query: str | None,
        category: str | None,
        difficulty: str | None,
        tags: list[str] | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        filters = [
            "c.deleted_at IS NULL",
            "c.visibility = 'PUBLISHED'",
            "v.status = 'READY'",
        ]
        params: dict[str, object] = {}

        if query:
            filters.append("(c.title ILIKE :like OR c.description ILIKE :like)")
            params["like"] = f"%{query}%"
        if category:
            filters.append("c.category = :category")
            params["category"] = category
        if difficulty:
            filters.append("c.difficulty = :difficulty")
            params["difficulty"] = difficulty
        if tags:
            filters.append("c.tags && :tags::text[]")
            params["tags"] = tags

        where_clause = " AND ".join(filters)
        base_from = (
            "FROM course.courses c "
            "JOIN publishing.course_versions v ON v.id = c.current_version_id "
            f"WHERE {where_clause}"
        )

        count_query = text(f"SELECT COUNT(*) {base_from}")
        total_result = await self._session.execute(count_query, params)
        total = int(total_result.scalar_one())

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        data_query = text(
            "SELECT c.id, c.title, c.short_description, c.category, c.difficulty, c.description "
            f"{base_from} "
            "ORDER BY c.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        )
        result = await self._session.execute(data_query, params)
        rows = result.mappings().all()
        return [dict(row) for row in rows], total

    async def get_ready_version_id(self, course_id: UUID) -> UUID | None:
        query = text(
            """
            SELECT c.current_version_id
              FROM course.courses c
              JOIN publishing.course_versions v ON v.id = c.current_version_id
             WHERE c.id = :course_id
               AND c.visibility = 'PUBLISHED'
               AND v.status = 'READY'
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        return result.scalar_one_or_none()

    async def get_module_titles(self, course_id: UUID) -> dict[UUID, str]:
        query = text(
            """
            SELECT id, title
              FROM course.modules
             WHERE course_id = :course_id
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        rows = result.mappings().all()
        return {row["id"]: row["title"] for row in rows}

    async def get_asset_titles(self, course_id: UUID) -> dict[UUID, str]:
        query = text(
            """
            SELECT a.id, a.title
              FROM course.assets a
              JOIN course.modules m ON m.id = a.module_id
             WHERE m.course_id = :course_id
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        rows = result.mappings().all()
        return {row["id"]: row["title"] for row in rows}
