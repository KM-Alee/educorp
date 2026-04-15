from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.repositories.course_repository import CourseRepository
from app.repositories.module_repository import ModuleRepository
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate, CourseListItem, ModuleOut
from app.services.slug_service import SlugService
from educorp_common.errors import ConflictError, ForbiddenError, NotFoundError


def _parse_duration(value: str | None) -> timedelta | None:
    """Parse an ISO 8601 duration like 'PT40H' into a timedelta."""
    if not value:
        return None
    import re

    match = re.match(
        r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", value, re.IGNORECASE
    )
    if not match:
        return None
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def _format_duration(td: timedelta | None) -> str | None:
    """Format a timedelta as ISO 8601 duration string."""
    if td is None:
        return None
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = ["PT"]
    if hours:
        parts.append(f"{hours}H")
    if minutes:
        parts.append(f"{minutes}M")
    if seconds or not (hours or minutes):
        parts.append(f"{seconds}S")
    return "".join(parts)


class CourseService:
    """Course CRUD, catalog, and ownership logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CourseRepository(session)
        self._module_repo = ModuleRepository(session)
        self._slug = SlugService(self._repo)

    async def create_course(
        self, *, data: CourseCreate, instructor_id: UUID
    ) -> CourseOut:
        slug = await self._slug.generate(data.title)
        course = Course(
            instructor_id=instructor_id,
            title=data.title,
            slug=slug,
            description=data.description,
            short_description=data.short_description,
            category=data.category,
            difficulty=data.difficulty,
            estimated_duration=_parse_duration(data.estimated_duration),
            tags=data.tags,
            max_capacity=data.max_capacity,
            prerequisites=[str(p) for p in data.prerequisites],
            visibility="DRAFT",
        )
        course = await self._repo.create(course)
        return self._to_out(course)

    async def get_course(
        self,
        course_id: UUID,
        *,
        caller_id: UUID | None = None,
        caller_roles: list[str] | None = None,
    ) -> CourseOut:
        course = await self._get_or_404(course_id)
        roles = caller_roles or []
        if not self._can_view(course, caller_id, roles):
            raise ForbiddenError("You do not have access to this course")
        modules = await self._module_repo.list_for_course(course_id)
        from app.repositories.asset_repository import AssetRepository

        asset_repo = AssetRepository(self._session)
        module_outs = []
        for m in modules:
            count = await asset_repo.count_for_module(m.id)
            module_outs.append(
                ModuleOut(
                    id=m.id,
                    title=m.title,
                    description=m.description,
                    sort_order=m.sort_order,
                    is_required=m.is_required,
                    asset_count=count,
                )
            )
        out = self._to_out(course)
        out.modules = module_outs
        return out

    async def update_course(
        self, *, course_id: UUID, data: CourseUpdate, caller_id: UUID, caller_roles: list[str]
    ) -> CourseOut:
        course = await self._get_or_404(course_id)
        self._enforce_owner_or_admin(course, caller_id, caller_roles)

        if course.visibility != "DRAFT":
            raise ForbiddenError("Only draft courses can be edited")

        fields = data.model_dump(exclude_unset=True)
        title_changed = "title" in fields and fields["title"] != course.title

        for key, value in fields.items():
            if key == "estimated_duration":
                setattr(course, key, _parse_duration(value))
            elif key == "prerequisites":
                setattr(course, key, [str(p) for p in value] if value else [])
            else:
                setattr(course, key, value)

        if title_changed:
            course.slug = await self._slug.generate(course.title, exclude_id=course.id)

        course = await self._repo.update(course)
        await self._session.refresh(course)
        return self._to_out(course)

    async def soft_delete_course(
        self, *, course_id: UUID, caller_id: UUID, caller_roles: list[str]
    ) -> None:
        course = await self._get_or_404(course_id)
        self._enforce_owner_or_admin(course, caller_id, caller_roles)
        await self._repo.soft_delete(course)

    async def get_course_for_publish(
        self,
        *,
        course_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> Course:
        course = await self._get_or_404(course_id)
        self._enforce_owner_or_admin(course, caller_id, caller_roles)
        if course.visibility != "DRAFT":
            raise ConflictError("Only draft courses can be published")
        return course

    async def list_courses(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
        visibility: str | None = None,
        instructor_id: UUID | None = None,
        include_drafts: bool = False,
    ) -> tuple[list[CourseListItem], int]:
        courses, total = await self._repo.list_courses(
            page=page,
            page_size=page_size,
            category=category,
            difficulty=difficulty,
            search=search,
            visibility=visibility,
            instructor_id=instructor_id,
            include_drafts=include_drafts,
        )
        items = [self._to_list_item(c) for c in courses]
        return items, total

    # ---- helpers ----

    async def _get_or_404(self, course_id: UUID) -> Course:
        course = await self._repo.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        return course

    @staticmethod
    def _enforce_owner_or_admin(
        course: Course, caller_id: UUID, caller_roles: list[str]
    ) -> None:
        if "admin" in caller_roles:
            return
        if course.instructor_id != caller_id:
            raise ForbiddenError("You do not own this course")

    @staticmethod
    def _can_view(course: Course, caller_id: UUID | None, caller_roles: list[str]) -> bool:
        if course.visibility == "PUBLISHED":
            return True
        if caller_id is None:
            return False
        if "admin" in caller_roles:
            return True
        return course.instructor_id == caller_id

    @staticmethod
    def _to_out(course: Course) -> CourseOut:
        return CourseOut(
            id=course.id,
            instructor_id=course.instructor_id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            short_description=course.short_description,
            category=course.category,
            difficulty=course.difficulty,
            estimated_duration=_format_duration(course.estimated_duration),
            tags=course.tags or [],
            thumbnail_url=course.thumbnail_url,
            is_public_preview=course.is_public_preview,
            max_capacity=course.max_capacity,
            prerequisites=course.prerequisites or [],
            visibility=course.visibility,
            current_version_id=course.current_version_id,
            modules=[],
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    @staticmethod
    def _to_list_item(course: Course) -> CourseListItem:
        return CourseListItem(
            id=course.id,
            instructor_id=course.instructor_id,
            title=course.title,
            slug=course.slug,
            short_description=course.short_description,
            category=course.category,
            difficulty=course.difficulty,
            estimated_duration=_format_duration(course.estimated_duration),
            tags=course.tags or [],
            thumbnail_url=course.thumbnail_url,
            visibility=course.visibility,
            created_at=course.created_at,
        )
