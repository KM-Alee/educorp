from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_minio, get_session
from app.main import create_app
from app.schemas.module import ModuleDetail
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


def _sample_module(course_id, **overrides) -> MagicMock:
    now = datetime.now(timezone.utc)
    m = MagicMock()
    m.id = overrides.get("id", uuid4())
    m.course_id = course_id
    m.title = overrides.get("title", "Module 1")
    m.description = overrides.get("description", "Desc")
    m.sort_order = overrides.get("sort_order", 0)
    m.is_required = overrides.get("is_required", True)
    m.estimated_duration = None
    m.created_at = now
    m.updated_at = now
    return m


class TestCreateModule:
    """POST /api/v1/courses/{course_id}/modules"""

    async def test_create_success(self, instructor, instructor_id, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        module_mock = _sample_module(course_id)
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.modules.ModuleService") as MockSvc:
            instance = MockSvc.return_value
            instance.create = AsyncMock(return_value=module_mock)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/courses/{course_id}/modules",
                    json={"title": "Module 1"},
                )
            assert resp.status_code == 201
            body = resp.json()
            assert body["data"]["title"] == "Module 1"

        app.dependency_overrides.clear()

    async def test_create_missing_title(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/courses/{uuid4()}/modules",
                json={},
            )
        assert resp.status_code == 422

        app.dependency_overrides.clear()

    async def test_create_forbidden_for_student(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/courses/{uuid4()}/modules",
                json={"title": "Nope"},
            )
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestListModules:
    """GET /api/v1/courses/{course_id}/modules"""

    async def test_list_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        modules = [_sample_module(course_id, sort_order=i) for i in range(3)]
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.modules.ModuleService") as MockSvc:
            instance = MockSvc.return_value
            instance.list_for_course = AsyncMock(return_value=modules)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/courses/{course_id}/modules")
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 3

        app.dependency_overrides.clear()


class TestUpdateModule:
    """PATCH /api/v1/courses/{course_id}/modules/{module_id}"""

    async def test_update_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        module_mock = _sample_module(course_id, title="Updated")
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.modules.ModuleService") as MockSvc:
            instance = MockSvc.return_value
            instance.update = AsyncMock(return_value=module_mock)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    f"/api/v1/courses/{course_id}/modules/{module_mock.id}",
                    json={"title": "Updated"},
                )
            assert resp.status_code == 200
            assert resp.json()["data"]["title"] == "Updated"

        app.dependency_overrides.clear()


class TestDeleteModule:
    """DELETE /api/v1/courses/{course_id}/modules/{module_id}"""

    async def test_delete_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.modules.ModuleService") as MockSvc:
            instance = MockSvc.return_value
            instance.delete = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    f"/api/v1/courses/{uuid4()}/modules/{uuid4()}"
                )
            assert resp.status_code == 204

        app.dependency_overrides.clear()


class TestReorderModules:
    """PATCH /api/v1/courses/{course_id}/modules/reorder"""

    async def test_reorder_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        ids = [uuid4(), uuid4()]
        modules = [
            _sample_module(course_id, id=ids[0], sort_order=0),
            _sample_module(course_id, id=ids[1], sort_order=1),
        ]
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.modules.ModuleService") as MockSvc:
            instance = MockSvc.return_value
            instance.reorder = AsyncMock(return_value=modules)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    f"/api/v1/courses/{course_id}/modules/reorder",
                    json={"order": [str(i) for i in ids]},
                )
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 2

        app.dependency_overrides.clear()
