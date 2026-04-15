from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models.course_version import CourseVersion
from app.models.publishing_step import PublishingStep
from app.models.version_artifact import VersionArtifact
from app.models.version_manifest import VersionManifest
from app.models.version_manifest_asset import VersionManifestAsset
from app.models.version_manifest_module import VersionManifestModule
from app.repositories.course_version_repository import CourseVersionRepository
from app.repositories.publishing_step_repository import PublishingStepRepository
from app.repositories.version_artifact_repository import VersionArtifactRepository
from app.repositories.version_manifest_repository import VersionManifestRepository
from app.schemas.version import PublishVersionRequest
from app.services.artifact_storage_service import ArtifactStorageService
from educorp_common.errors import EduCorpError, NotFoundError, ValidationError

PUBLISHING_STEPS = [
    "preflight_review",
    "extract_text",
    "chunk_content",
    "generate_embeddings",
    "index_qdrant",
    "finalize_version",
]


class PublishingVersionService:
    """Publishing version lifecycle management (Phase 3)."""

    def __init__(self, session, artifact_storage: ArtifactStorageService | None = None) -> None:
        self._session = session
        self._versions = CourseVersionRepository(session)
        self._steps = PublishingStepRepository(session)
        self._manifests = VersionManifestRepository(session)
        self._artifacts = VersionArtifactRepository(session)
        self._artifact_storage = artifact_storage

    async def create_version(
        self, *, manifest: PublishVersionRequest, initiated_by: UUID
    ) -> CourseVersion:
        if self._artifact_storage is None:
            raise RuntimeError("Artifact storage is required to create publishing versions")

        existing = await self._versions.get_active_publishing_for_course(manifest.course_id)
        if existing is not None:
            raise EduCorpError(
                code="PUBLISHING_IN_PROGRESS",
                message="Publishing already in progress for this course",
                status_code=409,
            )

        version_id = uuid4()
        now = datetime.now(timezone.utc)
        total_assets = sum(len(module.assets) for module in manifest.modules)
        version = CourseVersion(
            id=version_id,
            course_id=manifest.course_id,
            version_number=await self._versions.next_version_number(manifest.course_id),
            status="PREPARING",
            approval_state="PENDING",
            initiated_by=initiated_by,
            workflow_id=f"publish-{version_id}",
            processing_started_at=now,
            manifest_hash="pending",
            total_assets=total_assets,
        )
        await self._versions.create(version)

        manifest_record = VersionManifest(
            version_id=version_id,
            course_id=manifest.course_id,
            instructor_id=manifest.instructor_id,
            title=manifest.title,
            slug=manifest.slug,
            description=manifest.description,
            short_description=manifest.short_description,
            category=manifest.category,
            difficulty=manifest.difficulty,
            estimated_duration=manifest.estimated_duration,
            tags=manifest.tags,
            generated_at=manifest.generated_at,
        )
        await self._manifests.create(manifest_record)

        module_records = await self._manifests.create_modules(
            [
                VersionManifestModule(
                    version_id=version_id,
                    manifest_id=manifest_record.id,
                    module_id=module.id,
                    title=module.title,
                    description=module.description,
                    sort_order=module.sort_order,
                    is_required=module.is_required,
                    estimated_duration=module.estimated_duration,
                )
                for module in manifest.modules
            ]
        )
        module_map = {record.module_id: record.id for record in module_records}

        asset_records: list[VersionManifestAsset] = []
        for module in manifest.modules:
            for asset in module.assets:
                asset_records.append(
                    VersionManifestAsset(
                        version_id=version_id,
                        manifest_id=manifest_record.id,
                        manifest_module_id=module_map[module.id],
                        asset_id=asset.id,
                        module_id=module.id,
                        title=asset.title,
                        asset_type=asset.asset_type,
                        file_name=asset.file_name,
                        file_size=asset.file_size,
                        mime_type=asset.mime_type,
                        storage_path=asset.storage_path,
                        checksum=asset.checksum,
                        sort_order=asset.sort_order,
                    )
                )
        await self._manifests.create_assets(asset_records)

        manifest_payload = manifest.model_dump(mode="json")
        stored_manifest = await self._artifact_storage.put_json(
            f"versions/{version_id}/manifest/manifest.json",
            manifest_payload,
        )
        version.manifest_hash = stored_manifest.sha256
        await self._versions.update(version)

        await self._artifacts.create(
            VersionArtifact(
                version_id=version_id,
                artifact_type="MANIFEST",
                object_path=stored_manifest.object_path,
                sha256=stored_manifest.sha256,
                content_type=stored_manifest.content_type,
                size_bytes=stored_manifest.size_bytes,
                artifact_metadata={"kind": "manifest"},
            )
        )

        steps = [
            PublishingStep(version_id=version_id, step_name=step, status="PENDING")
            for step in PUBLISHING_STEPS
        ]
        await self._steps.create_many(steps)

        return version

    async def get_status(
        self, *, version_id: UUID
    ) -> tuple[CourseVersion, list[PublishingStep], list[VersionArtifact]]:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")

        steps = await self._steps.list_for_version(version_id)
        artifacts = await self._artifacts.list_for_version(version_id)
        return version, steps, artifacts

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

    async def mark_approval_requested(
        self, *, version_id: UUID, approved: bool
    ) -> CourseVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        if version.status != "REVIEW_REQUIRED":
            raise ValidationError("Only versions in review can be approved or rejected")
        version.approval_state = "APPROVED" if approved else "REJECTED"
        return await self._versions.update(version)

    async def prepare_retry(self, *, version_id: UUID) -> CourseVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundError("Publishing version not found")
        if version.status != "FAILED":
            raise ValidationError("Only failed versions can be retried")
        version.status = "PREPARING"
        version.approval_state = "PENDING"
        version.error_details = None
        version.preflight_summary_json = None
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
        if version.status not in {"PREPARING", "REVIEW_REQUIRED", "PUBLISHING"}:
            raise ValidationError("Only in-flight versions can be cancelled")
        version.status = "CANCELLED"
        version.processing_completed_at = datetime.now(timezone.utc)
        await self._versions.update(version)
        await self._steps.mark_skipped_for_version(version_id)
        return version
