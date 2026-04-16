"""Phase 3 tests: activation, display_status, cleanup, and version lifecycle."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.version import PublishingVersionOut, PublishingStepOut, PublishingArtifactOut
from app.services.version_service import PublishingVersionService
from educorp_common.errors import NotFoundError, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_version(**overrides):
    """Build a minimal CourseVersion-like SimpleNamespace."""
    from types import SimpleNamespace

    defaults = dict(
        id=uuid4(),
        course_id=uuid4(),
        version_number=1,
        status="READY",
        approval_state="APPROVED",
        initiated_by=uuid4(),
        workflow_id="wf-123",
        run_id="run-abc",
        manifest_hash="abc123",
        preflight_summary_json=None,
        error_details=None,
        total_chunks=0,
        total_assets=0,
        processing_started_at=None,
        processing_completed_at=None,
        ready_at=datetime.now(timezone.utc),
        activated_at=None,
        superseded_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_version_out(**overrides) -> PublishingVersionOut:
    base = dict(
        id=uuid4(),
        course_id=uuid4(),
        version_number=1,
        status="READY",
        approval_state="APPROVED",
        initiated_by=uuid4(),
        workflow_id="wf-test",
        run_id=None,
        manifest_hash="abc",
        preflight_summary_json=None,
        error_details=None,
        total_chunks=10,
        total_assets=2,
        processing_started_at=None,
        processing_completed_at=None,
        created_at=datetime.now(timezone.utc),
        ready_at=datetime.now(timezone.utc),
        activated_at=None,
        superseded_at=None,
        steps=[],
        artifacts=[],
    )
    base.update(overrides)
    return PublishingVersionOut(**base)


# ---------------------------------------------------------------------------
# display_status tests
# ---------------------------------------------------------------------------


class TestDisplayStatus:
    def test_ready_not_activated(self) -> None:
        v = _make_version_out(status="READY", activated_at=None)
        assert v.display_status == "READY"

    def test_ready_and_activated(self) -> None:
        v = _make_version_out(status="READY", activated_at=datetime.now(timezone.utc))
        assert v.display_status == "ACTIVATED"

    def test_review_required_pending(self) -> None:
        v = _make_version_out(status="REVIEW_REQUIRED", approval_state="PENDING")
        assert v.display_status == "REVIEW_REQUIRED"

    def test_review_required_approved(self) -> None:
        v = _make_version_out(status="REVIEW_REQUIRED", approval_state="APPROVED")
        assert v.display_status == "APPROVED"

    def test_publishing_status(self) -> None:
        v = _make_version_out(status="PUBLISHING")
        assert v.display_status == "PUBLISHING"

    def test_failed_status(self) -> None:
        v = _make_version_out(status="FAILED")
        assert v.display_status == "FAILED"

    def test_cancelled_status(self) -> None:
        v = _make_version_out(status="CANCELLED")
        assert v.display_status == "CANCELLED"

    def test_superseded_status(self) -> None:
        v = _make_version_out(status="SUPERSEDED", superseded_at=datetime.now(timezone.utc))
        assert v.display_status == "SUPERSEDED"


# ---------------------------------------------------------------------------
# Version service — activate_version
# ---------------------------------------------------------------------------


class TestActivateVersion:
    def _make_service(self) -> tuple[PublishingVersionService, MagicMock, MagicMock]:
        session = MagicMock()
        svc = PublishingVersionService(session)
        versions_repo = AsyncMock()
        steps_repo = AsyncMock()
        svc._versions = versions_repo
        svc._steps = steps_repo
        return svc, versions_repo, steps_repo

    @pytest.mark.asyncio
    async def test_activate_ready_version(self) -> None:
        svc, versions_repo, _steps = self._make_service()
        vid = uuid4()
        course_id = uuid4()
        version = _make_version(id=vid, course_id=course_id, status="READY", activated_at=None)
        versions_repo.get_by_id = AsyncMock(return_value=version)
        versions_repo.get_active_version_id_for_course = AsyncMock(return_value=None)
        versions_repo.update = AsyncMock(return_value=version)

        result, superseded_id = await svc.activate_version(version_id=vid)

        assert result.activated_at is not None
        assert superseded_id is None
        versions_repo.update.assert_called()

    @pytest.mark.asyncio
    async def test_activate_supersedes_previous(self) -> None:
        svc, versions_repo, _steps = self._make_service()
        vid = uuid4()
        old_id = uuid4()
        course_id = uuid4()
        version = _make_version(id=vid, course_id=course_id, status="READY", activated_at=None)
        old_version = _make_version(
            id=old_id, course_id=course_id, status="READY",
            activated_at=datetime.now(timezone.utc)
        )
        versions_repo.get_by_id = AsyncMock(side_effect=lambda v: version if v == vid else old_version)
        versions_repo.get_active_version_id_for_course = AsyncMock(return_value=old_id)
        versions_repo.update = AsyncMock(side_effect=lambda v: v)

        result, superseded_id = await svc.activate_version(version_id=vid)

        assert superseded_id == old_id
        assert old_version.status == "SUPERSEDED"
        assert old_version.superseded_at is not None

    @pytest.mark.asyncio
    async def test_activate_non_ready_raises(self) -> None:
        svc, versions_repo, _steps = self._make_service()
        vid = uuid4()
        version = _make_version(id=vid, status="PUBLISHING")
        versions_repo.get_by_id = AsyncMock(return_value=version)

        with pytest.raises(ValidationError):
            await svc.activate_version(version_id=vid)

    @pytest.mark.asyncio
    async def test_activate_not_found_raises(self) -> None:
        svc, versions_repo, _steps = self._make_service()
        versions_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.activate_version(version_id=uuid4())


# ---------------------------------------------------------------------------
# Version service — get_superseded_versions_for_cleanup
# ---------------------------------------------------------------------------


class TestCleanupVersions:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self) -> None:
        session = MagicMock()
        svc = PublishingVersionService(session)
        versions_repo = AsyncMock()
        svc._versions = versions_repo

        old_v = _make_version(status="SUPERSEDED", superseded_at=datetime.now(timezone.utc) - timedelta(days=10))
        versions_repo.list_superseded_before_retention = AsyncMock(return_value=[old_v])

        results = await svc.get_superseded_versions_for_cleanup(retention_days=7)

        assert len(results) == 1
        versions_repo.list_superseded_before_retention.assert_called_once_with(retention_days=7)
