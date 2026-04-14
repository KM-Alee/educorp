from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models.course_version import CourseVersion
from app.models.publishing_step import PublishingStep
from app.repositories.course_version_repository import CourseVersionRepository
from app.repositories.publishing_step_repository import PublishingStepRepository
from educorp_common.errors import EduCorpError, NotFoundError, ValidationError

PUBLISHING_STEPS = [
    "validate_assets",
    "extract_text",
    "chunk_content",
    "generate_embeddings",
    "index_qdrant",
    "finalize_version",
]


class PublishingVersionService:
    """Publishing version lifecycle management (Phase 3)."""

    def __init__(self, session) -> None:
        self._versions = CourseVersionRepository(session)
        self._steps = PublishingStepRepository(session)

    async def create_version(self, *, course_id: UUID, initiated_by: UUID) -> CourseVersion:
        existing = await self._versions.get_active_publishing_for_course(course_id)
        if existing is not None:
            raise EduCorpError(
                code="PUBLISHING_IN_PROGRESS",
                message="Publishing already in progress for this course",
                status_code=409,
            )

        version_id = uuid4()
        now = datetime.now(timezone.utc)
        version = CourseVersion(
            id=version_id,
            course_id=course_id,
            version_number=await self._versions.next_version_number(course_id),
            status="PUBLISHING",
            initiated_by=initiated_by,
            workflow_id=f"publish-{version_id}",
            processing_started_at=now,
        )
        await self._versions.create(version)

        steps = [
            PublishingStep(version_id=version_id, step_name=step, status="PENDING")
            for step in PUBLISHING_STEPS
        ]
        await self._steps.create_many(steps)

        return version

    async def get_status(
        self, *, version_id: UUID
    ) -> tuple[CourseVersion, list[PublishingStep]]:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")

        steps = await self._steps.list_for_version(version_id)
        return version, steps

    async def attach_run_id(self, *, version_id: UUID, run_id: str) -> CourseVersion:
        version = await self._versions.set_run_id(version_id, run_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        return version

    async def mark_failed(
        self, *, version_id: UUID, error_details: dict | None = None
    ) -> CourseVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        version.status = "FAILED"
        version.error_details = error_details
        version.processing_completed_at = datetime.now(timezone.utc)
        return await self._versions.update(version)

    async def prepare_retry(self, *, version_id: UUID) -> CourseVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        if version.status != "FAILED":
            raise ValidationError("Only failed versions can be retried")
        version.status = "PUBLISHING"
        version.error_details = None
        version.processing_started_at = datetime.now(timezone.utc)
        version.processing_completed_at = None
        version.ready_at = None
        await self._versions.update(version)
        await self._steps.reset_for_version(version_id)
        return version

    async def mark_cancelled(self, *, version_id: UUID) -> CourseVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        if version.status != "PUBLISHING":
            raise ValidationError("Only publishing versions can be cancelled")
        version.status = "CANCELLED"
        version.processing_completed_at = datetime.now(timezone.utc)
        await self._versions.update(version)
        await self._steps.mark_skipped_for_version(version_id)
        return version
