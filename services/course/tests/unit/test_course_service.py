from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.course_service import CourseService


def _course() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        instructor_id=uuid4(),
        title="Original title",
        slug="original-title",
        description="Original description",
        short_description="Original short",
        category="CS",
        difficulty="beginner",
        estimated_duration=timedelta(hours=2),
        tags=["phase3"],
        thumbnail_url=None,
        is_public_preview=False,
        max_capacity=None,
        prerequisites=[],
        visibility="DRAFT",
        current_version_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _module(sort_order: int, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        description=f"{title} description",
        sort_order=sort_order,
        is_required=True,
        estimated_duration=timedelta(minutes=45),
    )


def _asset(title: str, sort_order: int, checksum: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        asset_type="pdf",
        file_name=f"{title}.pdf",
        file_size=128,
        mime_type="application/pdf",
        storage_path=f"raw/{checksum}",
        checksum=checksum,
        sort_order=sort_order,
        upload_status="UPLOADED",
    )


class TestCourseServicePublishSnapshot:
    async def test_build_publish_snapshot_is_immutable(self) -> None:
        session = MagicMock()
        svc = CourseService(session)
        course = _course()
        module = _module(0, "Week 1")
        asset = _asset("Slides", 0, "abc123")

        svc.get_course_for_publish = AsyncMock(return_value=course)
        svc._module_repo = MagicMock()
        svc._module_repo.list_for_course = AsyncMock(return_value=[module])
        svc._asset_repo = MagicMock()
        svc._asset_repo.list_for_module = AsyncMock(return_value=[asset])

        snapshot = await svc.build_publish_snapshot(
            course_id=course.id,
            caller_id=course.instructor_id,
            caller_roles=["instructor"],
        )

        course.title = "Edited title"
        module.title = "Reordered Week"
        asset.checksum = "changed"

        assert snapshot.title == "Original title"
        assert snapshot.modules[0].title == "Week 1"
        assert snapshot.modules[0].assets[0].checksum == "abc123"

    async def test_editing_draft_after_publish_does_not_change_snapshot_order(self) -> None:
        session = MagicMock()
        svc = CourseService(session)
        course = _course()
        module_a = _module(0, "Week 1")
        module_b = _module(1, "Week 2")

        svc.get_course_for_publish = AsyncMock(return_value=course)
        svc._module_repo = MagicMock()
        svc._module_repo.list_for_course = AsyncMock(return_value=[module_a, module_b])
        svc._asset_repo = MagicMock()
        svc._asset_repo.list_for_module = AsyncMock(side_effect=[[], []])

        snapshot = await svc.build_publish_snapshot(
            course_id=course.id,
            caller_id=course.instructor_id,
            caller_roles=["instructor"],
        )

        module_a.sort_order = 5
        module_b.sort_order = 0
        module_a.title = "Moved later"
        module_b.title = "Moved earlier"

        assert [module.title for module in snapshot.modules] == ["Week 1", "Week 2"]
        assert [module.sort_order for module in snapshot.modules] == [0, 1]