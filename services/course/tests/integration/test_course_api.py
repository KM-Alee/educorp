from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_minio, get_session
from app.main import create_app
from app.schemas.course import CourseListItem, CourseOut
from app.schemas.publishing import (
    PublishManifest,
    PublishManifestAsset,
    PublishManifestModule,
    PublishVersionResponse,
)
from educorp_common.auth.dependencies import CurrentUser


@pytest.fixture
def instructor_id():
    return uuid4()


@pytest.fixture
def instructor(instructor_id) -> CurrentUser:
    return CurrentUser(
        id=str(instructor_id),
        email="inst@test.com",
        roles=["instructor"],
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def student() -> CurrentUser:
    return CurrentUser(
        id=str(uuid4()),
        email="student@test.com",
        roles=["student"],
        is_active=True,
        is_verified=True,
    )


def _make_auth(user):
    async def _override():
        return user
    return _override


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_minio():
    return AsyncMock()


def _sample_course_out(instructor_id, **overrides) -> CourseOut:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid4(),
        instructor_id=instructor_id,
        title="Test Course",
        slug="test-course",
        description="A test course",
        short_description="Short desc",
        category="CS",
        difficulty="beginner",
        estimated_duration="PT10H",
        tags=["python"],
        thumbnail_url=None,
        is_public_preview=False,
        max_capacity=None,
        prerequisites=[],
        visibility="DRAFT",
        current_version_id=None,
        modules=[],
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return CourseOut(**defaults)


def _sample_list_item(instructor_id, **overrides) -> CourseListItem:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid4(),
        instructor_id=instructor_id,
        title="Test Course",
        slug="test-course",
        short_description="Short desc",
        category="CS",
        difficulty="beginner",
        estimated_duration="PT10H",
        tags=["python"],
        thumbnail_url=None,
        visibility="DRAFT",
        created_at=now,
    )
    defaults.update(overrides)
    return CourseListItem(**defaults)


class TestCreateCourse:
    """POST /api/v1/courses/"""

    async def test_create_success(self, instructor, instructor_id, mock_session, mock_minio):
        app = create_app()
        course_out = _sample_course_out(instructor_id)
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.create_course = AsyncMock(return_value=course_out)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/courses/",
                    json={"title": "Test Course"},
                )
            assert resp.status_code == 201
            body = resp.json()
            assert body["data"]["title"] == "Test Course"
            assert "meta" in body

        app.dependency_overrides.clear()

    async def test_create_missing_title(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/courses/", json={})
        assert resp.status_code == 422

        app.dependency_overrides.clear()

    async def test_create_requires_instructor_role(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/courses/",
                json={"title": "Should Fail"},
            )
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestGetCourse:
    """GET /api/v1/courses/{course_id}"""

    async def test_get_found(self, instructor, instructor_id, mock_session, mock_minio):
        app = create_app()
        course_out = _sample_course_out(instructor_id)
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_course = AsyncMock(return_value=course_out)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/courses/{course_out.id}")
            assert resp.status_code == 200
            assert resp.json()["data"]["id"] == str(course_out.id)

        app.dependency_overrides.clear()

    async def test_get_not_found(self, instructor, mock_session, mock_minio):
        from educorp_common.errors import NotFoundError

        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_course = AsyncMock(side_effect=NotFoundError("Course not found"))

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/courses/{uuid4()}")
            assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestListCourses:
    """GET /api/v1/courses/"""

    async def test_list_empty(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.list_courses = AsyncMock(return_value=([], 0))

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/courses/")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"] == []
            assert body["pagination"]["total_items"] == 0

        app.dependency_overrides.clear()

    async def test_list_with_results(self, instructor, instructor_id, mock_session, mock_minio):
        app = create_app()
        item = _sample_list_item(instructor_id)
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.list_courses = AsyncMock(return_value=([item], 1))

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/courses/?page=1&page_size=10")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["data"]) == 1
            assert body["pagination"]["total_items"] == 1

        app.dependency_overrides.clear()


class TestUpdateCourse:
    """PATCH /api/v1/courses/{course_id}"""

    async def test_update_success(self, instructor, instructor_id, mock_session, mock_minio):
        app = create_app()
        course_out = _sample_course_out(instructor_id, title="Updated Title")
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_course = AsyncMock(return_value=course_out)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    f"/api/v1/courses/{course_out.id}",
                    json={"title": "Updated Title"},
                )
            assert resp.status_code == 200
            assert resp.json()["data"]["title"] == "Updated Title"

        app.dependency_overrides.clear()

    async def test_update_forbidden_for_student(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"/api/v1/courses/{uuid4()}",
                json={"title": "Nope"},
            )
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestDeleteCourse:
    """DELETE /api/v1/courses/{course_id}"""

    async def test_delete_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.soft_delete_course = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(f"/api/v1/courses/{uuid4()}")
            assert resp.status_code == 204

        app.dependency_overrides.clear()

    async def test_delete_forbidden_for_student(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/courses/{uuid4()}")
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestPublishCourse:
    async def test_publish_forwards_manifest_snapshot(
        self, instructor, instructor_id, mock_session, mock_minio
    ):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        snapshot = PublishManifest(
            course_id=uuid4(),
            instructor_id=instructor_id,
            requested_by=instructor_id,
            title="Snapshot Course",
            slug="snapshot-course",
            description="Frozen draft",
            short_description="Short",
            category="CS",
            difficulty="beginner",
            estimated_duration="PT2H",
            tags=["phase3"],
            generated_at=datetime.now(timezone.utc),
            modules=[
                PublishManifestModule(
                    id=uuid4(),
                    title="Week 1",
                    description="Intro",
                    sort_order=0,
                    is_required=True,
                    estimated_duration="PT1H",
                    assets=[
                        PublishManifestAsset(
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

        publish_response = PublishVersionResponse(
            version_id=uuid4(),
            version_number=3,
            status="PREPARING",
            approval_state="PENDING",
            workflow_id="publish-test",
            message="Publishing started",
        )

        with patch("app.api.v1.courses.CourseService") as MockCourseSvc, patch(
            "app.api.v1.courses.DraftValidationService"
        ) as MockValidationSvc, patch("app.api.v1.courses.PublishingClient") as MockClient:
            course_service = MockCourseSvc.return_value
            course_service.get_course_for_publish = AsyncMock(return_value=object())
            course_service.build_publish_snapshot = AsyncMock(return_value=snapshot)

            validation_service = MockValidationSvc.return_value
            validation_service.validate = AsyncMock(return_value=[])

            client_service = MockClient.return_value
            client_service.create_version = AsyncMock(return_value=publish_response)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/courses/{snapshot.course_id}/publish")

            assert resp.status_code == 202
            client_service.create_version.assert_awaited_once()
            forwarded_manifest = client_service.create_version.await_args.kwargs["manifest"]
            assert forwarded_manifest.course_id == snapshot.course_id
            assert forwarded_manifest.modules[0].assets[0].checksum == "abc123"

        app.dependency_overrides.clear()


class TestActivateCourseVersion:
    async def test_activate_course_version_updates_course(
        self, admin_user, mock_session, mock_minio
    ):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(admin_user)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        course_id = uuid4()
        version_id = uuid4()
        course_out = _sample_course_out(
            uuid4(),
            id=course_id,
            visibility="PUBLISHED",
            current_version_id=version_id,
        )

        with patch("app.api.v1.courses.CourseService") as MockSvc:
            instance = MockSvc.return_value
            instance.activate_course_version = AsyncMock(return_value=course_out)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/courses/internal/{course_id}/activate-version",
                    json={"version_id": str(version_id)},
                )

            assert resp.status_code == 200
            instance.activate_course_version.assert_awaited_once_with(
                course_id=course_id,
                version_id=version_id,
            )
            assert resp.json()["data"]["current_version_id"] == str(version_id)

        app.dependency_overrides.clear()
