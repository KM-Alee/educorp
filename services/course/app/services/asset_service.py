from __future__ import annotations

from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.asset import Asset
from app.repositories.asset_repository import AssetRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.module_repository import ModuleRepository
from app.services.storage_service import StorageService
from educorp_common.middleware.correlation import get_correlation_id
from educorp_common.errors import ForbiddenError, NotFoundError, ValidationError
from educorp_common.inter_service_http import inter_service_request

logger = structlog.get_logger()


class AssetService:
    """Asset upload, list, download, and delete flows."""

    def __init__(self, session: AsyncSession, storage: StorageService) -> None:
        self._session = session
        self._courses = CourseRepository(session)
        self._modules = ModuleRepository(session)
        self._assets = AssetRepository(session)
        self._storage = storage

    async def upload(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
        file_name: str,
        content_type: str,
        data: bytes,
        title: str,
        sort_order: int | None = None,
    ) -> Asset:
        course = await self._get_course_for_edit(course_id, caller_id, caller_roles)
        module = await self._modules.get_by_id(module_id)
        if module is None or module.course_id != course.id:
            raise NotFoundError("Module not found")

        asset_type, mime = StorageService.validate_file(file_name, content_type, data)
        checksum = StorageService.compute_checksum(data)
        asset_id = uuid4()

        if sort_order is None:
            sort_order = await self._assets.next_sort_order(module_id)

        storage_path = StorageService.storage_path(course_id, module_id, asset_id, file_name)

        # Upload to MinIO first
        await self._storage.upload(storage_path, data, mime)

        # Persist metadata
        asset = Asset(
            id=asset_id,
            module_id=module_id,
            title=title,
            asset_type=asset_type,
            file_name=file_name,
            file_size=len(data),
            mime_type=mime,
            storage_path=storage_path,
            checksum=checksum,
            sort_order=sort_order,
            upload_status="UPLOADED",
        )
        try:
            asset = await self._assets.create(asset)
        except Exception:
            # Attempt to clean up the uploaded object on DB failure
            logger.warning(
                "DB insert failed after upload; cleaning up MinIO object", path=storage_path
            )
            await self._storage.delete(storage_path)
            raise

        return asset

    async def list_for_module(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> list[Asset]:
        course = await self._courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if not self._can_view(course.visibility, course.instructor_id, caller_id, caller_roles):
            raise ForbiddenError("You do not have access to this course")
        module = await self._modules.get_by_id(module_id)
        if module is None or module.course_id != course_id:
            raise NotFoundError("Module not found")
        return await self._assets.list_for_module(module_id)

    async def presigned_download(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        asset_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> str:
        asset = await self.get_downloadable_asset(
            course_id=course_id,
            module_id=module_id,
            asset_id=asset_id,
            caller_id=caller_id,
            caller_roles=caller_roles,
        )
        return await self._storage.presigned_url(asset.storage_path)

    async def get_downloadable_asset(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        asset_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> Asset:
        course = await self._courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        asset = await self._assets.get_by_id(asset_id)
        if asset is None or asset.module_id != module_id:
            raise NotFoundError("Asset not found")
        if not await self._can_download(course_id, course.instructor_id, caller_id, caller_roles):
            raise ForbiddenError("Access denied")
        return asset

    async def delete(
        self,
        *,
        course_id: UUID,
        module_id: UUID,
        asset_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> None:
        course = await self._get_course_for_edit(course_id, caller_id, caller_roles)
        module = await self._modules.get_by_id(module_id)
        if module is None or module.course_id != course.id:
            raise NotFoundError("Module not found")
        asset = await self._assets.get_by_id(asset_id)
        if asset is None or asset.module_id != module_id:
            raise NotFoundError("Asset not found")

        storage_path = asset.storage_path
        await self._assets.delete(asset)
        await self._storage.delete(storage_path)

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

    async def _can_download(
        self,
        course_id: UUID,
        instructor_id: UUID,
        caller_id: UUID,
        caller_roles: list[str],
    ) -> bool:
        if "admin" in caller_roles or instructor_id == caller_id:
            return True
        if "student" not in caller_roles:
            return False

        response = await inter_service_request(
            "GET",
            f"{settings.enrollment_service_url}/internal/courses/{course_id}/students/{caller_id}/enrollment-status",
            timeout=10.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Internal-Service-Token": settings.internal_service_token,
                "X-Correlation-Id": get_correlation_id(),
            },
        )

        try:
            payload = response.json() if response.content else None
        except ValueError:
            payload = None

        if response.is_error or not payload or "data" not in payload:
            return False

        return bool(payload["data"].get("is_enrolled"))
