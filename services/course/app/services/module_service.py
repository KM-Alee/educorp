from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import Module
from app.repositories.course_repository import CourseRepository
from app.repositories.module_repository import ModuleRepository
from educorp_common.errors import ForbiddenError, NotFoundError, ValidationError


class ModuleService:
    """Module CRUD and reorder logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._courses = CourseRepository(session)
        self._modules = ModuleRepository(session)

    async def create(
        self,
        *,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
        title: str,
        description: str | None = None,
        sort_order: int | None = None,
        is_required: bool = True,
    ) -> Module:
        course = await self._get_course_for_edit(course_id, caller_id, caller_roles)
        if sort_order is None:
            sort_order = await self._modules.next_sort_order(course.id)
        module = Module(
            course_id=course.id,
            title=title,
            description=description,
            sort_order=sort_order,
            is_required=is_required,
        )
        return await self._modules.create(module)

    async def list_for_course(
        self,
        course_id: UUID,
        *,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> list[Module]:
        course = await self._courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if not self._can_view(course.visibility, course.instructor_id, caller_id, caller_roles):
            raise ForbiddenError("You do not have access to this course")
        return await self._modules.list_for_course(course_id)

    async def update(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
        title: str | None = None,
        description: str | None = None,
        is_required: bool | None = None,
    ) -> Module:
        await self._get_course_for_edit(course_id, caller_id, caller_roles)
        module = await self._modules.get_by_id(module_id)
        if module is None or module.course_id != course_id:
            raise NotFoundError("Module not found")

        if title is not None:
            module.title = title
        if description is not None:
            module.description = description
        if is_required is not None:
            module.is_required = is_required

        return await self._modules.update(module)

    async def delete(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> None:
        await self._get_course_for_edit(course_id, caller_id, caller_roles)
        module = await self._modules.get_by_id(module_id)
        if module is None or module.course_id != course_id:
            raise NotFoundError("Module not found")
        await self._modules.delete(module)

    async def reorder(
        self,
        *,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
        ordered_ids: list[UUID],
    ) -> list[Module]:
        await self._get_course_for_edit(course_id, caller_id, caller_roles)
        existing = await self._modules.list_for_course(course_id)
        existing_ids = {m.id for m in existing}
        provided_ids = set(ordered_ids)

        if provided_ids != existing_ids:
            raise ValidationError("Provided module IDs do not match existing modules")
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValidationError("Duplicate module IDs in order list")

        await self._modules.reorder(course_id, ordered_ids)
        return await self._modules.list_for_course(course_id)

    async def _get_course_for_edit(self, course_id: UUID, caller_id: UUID, caller_roles: list[str]):
        course = await self._courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if course.visibility != "DRAFT":
            raise ForbiddenError("Only draft courses can be edited")
        if "admin" not in caller_roles and course.instructor_id != caller_id:
            raise ForbiddenError("You do not own this course")
        return course

    @staticmethod
    def _can_view(
        visibility: str,
        instructor_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> bool:
        if visibility == "PUBLISHED":
            return True
        if "admin" in caller_roles:
            return True
        return instructor_id == caller_id
