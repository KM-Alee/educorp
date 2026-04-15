from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.version import PublishManifestAssetIn, PublishManifestModuleIn, PublishVersionRequest
from app.services.version_service import PublishingVersionService
from educorp_common.errors import ValidationError


def _manifest() -> PublishVersionRequest:
    course_id = uuid4()
    requested_by = uuid4()
    return PublishVersionRequest(
        course_id=course_id,
        instructor_id=requested_by,
        requested_by=requested_by,
        title="Manifest course",
        slug="manifest-course",
        description="Immutable publish snapshot",
        short_description="Snapshot",
        category="CS",
        difficulty="beginner",
        estimated_duration="PT2H",
        tags=["phase3"],
        generated_at=datetime.now(timezone.utc),
        modules=[
            PublishManifestModuleIn(
                id=uuid4(),
                title="Week 1",
                description="Intro",
                sort_order=0,
                is_required=True,
                estimated_duration="PT45M",
                assets=[
                    PublishManifestAssetIn(
                        id=uuid4(),
                        title="Slides",
                        asset_type="pdf",
                        file_name="slides.pdf",
                        file_size=128,
                        mime_type="application/pdf",
                        storage_path="raw/abc123",
                        checksum="abc123",
                        sort_order=0,
                    )
                ],
            )
        ],
    )


class TestPublishingVersionService:
    async def test_create_version_persists_manifest_hash(self) -> None:
        session = MagicMock()
        storage = MagicMock()
        storage.put_json = AsyncMock(
            return_value=SimpleNamespace(
                object_path="versions/test-version/manifest/manifest.json",
                sha256="deadbeef",
                content_type="application/json",
                size_bytes=256,
            )
        )
        svc = PublishingVersionService(session, artifact_storage=storage)
        manifest = _manifest()

        svc._versions = MagicMock()
        svc._versions.get_active_publishing_for_course = AsyncMock(return_value=None)
        svc._versions.next_version_number = AsyncMock(return_value=1)
        svc._versions.create = AsyncMock(side_effect=lambda version: version)
        svc._versions.update = AsyncMock(side_effect=lambda version: version)

        svc._manifests = MagicMock()

        async def create_manifest(record):
            record.id = uuid4()
            return record

        async def create_modules(records):
            for record in records:
                record.id = uuid4()
            return records

        svc._manifests.create = AsyncMock(side_effect=create_manifest)
        svc._manifests.create_modules = AsyncMock(side_effect=create_modules)
        svc._manifests.create_assets = AsyncMock(side_effect=lambda assets: assets)

        svc._artifacts = MagicMock()
        svc._artifacts.create = AsyncMock()
        svc._steps = MagicMock()
        svc._steps.create_many = AsyncMock()

        version = await svc.create_version(manifest=manifest, initiated_by=manifest.requested_by)

        assert version.manifest_hash == "deadbeef"
        storage.put_json.assert_awaited_once()
        assert storage.put_json.await_args.args[0].endswith("/manifest/manifest.json")

        stored_artifact = svc._artifacts.create.await_args.args[0]
        assert stored_artifact.sha256 == "deadbeef"
        assert stored_artifact.artifact_type == "MANIFEST"

    async def test_mark_approval_requested_requires_review_state(self) -> None:
        session = MagicMock()
        svc = PublishingVersionService(session)
        version = SimpleNamespace(status="PREPARING", approval_state="PENDING")

        svc._versions = MagicMock()
        svc._versions.get_by_id = AsyncMock(return_value=version)

        with pytest.raises(ValidationError):
            await svc.mark_approval_requested(version_id=uuid4(), approved=True)

    async def test_prepare_retry_keeps_same_manifest_hash(self) -> None:
        session = MagicMock()
        svc = PublishingVersionService(session)
        version = SimpleNamespace(
            status="FAILED",
            manifest_hash="same-hash",
            approval_state="REJECTED",
            error_details={"message": "boom"},
            preflight_summary_json={"flagged_assets": 1},
            processing_started_at=None,
            processing_completed_at=datetime.now(timezone.utc),
            ready_at=datetime.now(timezone.utc),
        )

        svc._versions = MagicMock()
        svc._versions.get_by_id = AsyncMock(return_value=version)
        svc._versions.update = AsyncMock(side_effect=lambda updated: updated)
        svc._steps = MagicMock()
        svc._steps.reset_for_version = AsyncMock()

        retried = await svc.prepare_retry(version_id=uuid4())

        assert retried.status == "PREPARING"
        assert retried.approval_state == "PENDING"
        assert retried.manifest_hash == "same-hash"
        assert retried.preflight_summary_json is None
        assert retried.error_details is None