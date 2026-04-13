from __future__ import annotations

from uuid import UUID

from app.repositories.course_repository import CourseRepository
from app.repositories.module_repository import ModuleRepository
from app.schemas.common import DraftValidationIssue
from sqlalchemy.ext.asyncio import AsyncSession


class DraftValidationService:
    """Pre-publish validation rules for course drafts."""

    def __init__(self, session: AsyncSession) -> None:
        self._courses = CourseRepository(session)
        self._modules = ModuleRepository(session)

    async def validate(self, course_id: UUID) -> list[DraftValidationIssue]:
        issues: list[DraftValidationIssue] = []

        course = await self._courses.get_by_id(course_id)
        if course is None:
            issues.append(DraftValidationIssue(field="course", message="Course not found"))
            return issues

        if not course.title or not course.title.strip():
            issues.append(DraftValidationIssue(field="title", message="Title is required"))
        if not course.description or not course.description.strip():
            issues.append(DraftValidationIssue(field="description", message="Description is required"))
        if not course.category:
            issues.append(DraftValidationIssue(field="category", message="Category is required"))
        if not course.difficulty:
            issues.append(DraftValidationIssue(field="difficulty", message="Difficulty is required"))

        module_count = await self._modules.count_for_course(course_id)
        if module_count == 0:
            issues.append(DraftValidationIssue(field="modules", message="At least one module is required"))

        modules = await self._modules.list_for_course(course_id)
        for m in modules:
            if not m.title or not m.title.strip():
                issues.append(DraftValidationIssue(
                    field=f"modules[{m.sort_order}].title",
                    message="Module title is required",
                ))

        return issues
