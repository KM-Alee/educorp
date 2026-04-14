from __future__ import annotations

from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.course_repository import CourseRepository
from app.repositories.draft_content_repository import DraftContentRepository
from app.schemas.draft import DraftContentDocument
from educorp_common.errors import ForbiddenError, NotFoundError


class DraftContentService:
    """Course rich draft content stored in MongoDB."""

    def __init__(self, session: AsyncSession, mongo_db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._courses = CourseRepository(session)
        self._drafts = DraftContentRepository(mongo_db)

    async def get(
        self,
        *,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> DraftContentDocument:
        await self._get_course_for_authoring(course_id, caller_id, caller_roles)
        stored = await self._drafts.get(course_id)
        if stored is None:
            return DraftContentDocument(course_id=course_id, content={}, updated_at=None)

        return DraftContentDocument(
            course_id=course_id,
            content=stored.get("content", {}),
            updated_at=stored.get("updated_at"),
        )

    async def update(
        self,
        *,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
        content: dict[str, Any],
    ) -> DraftContentDocument:
        await self._get_course_for_authoring(course_id, caller_id, caller_roles)
        await self._drafts.upsert(course_id, content)
        stored = await self._drafts.get(course_id)
        return DraftContentDocument(
            course_id=course_id,
            content=stored.get("content", {}) if stored else {},
            updated_at=stored.get("updated_at") if stored else None,
        )

    async def _get_course_for_authoring(
        self,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> None:
        course = await self._courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if course.visibility != "DRAFT":
            raise ForbiddenError("Only draft courses can be edited")
        if "admin" not in caller_roles and course.instructor_id != caller_id:
            raise ForbiddenError("You do not own this course")