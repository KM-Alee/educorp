from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_minio, get_session
from app.main import create_app
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


def _sample_asset(module_id, **overrides) -> MagicMock:
    now = datetime.now(timezone.utc)
    a = MagicMock()
    a.id = overrides.get("id", uuid4())
    a.module_id = module_id
    a.title = overrides.get("title", "Lecture Notes")
    a.asset_type = overrides.get("asset_type", "pdf")
    a.file_name = overrides.get("file_name", "notes.pdf")
    a.file_size = overrides.get("file_size", 1024)
    a.mime_type = overrides.get("mime_type", "application/pdf")
    a.storage_path = overrides.get("storage_path", "course-assets/x/y/z/notes.pdf")
    a.checksum = overrides.get("checksum", "abc123")
    a.sort_order = overrides.get("sort_order", 0)
    a.upload_status = overrides.get("upload_status", "UPLOADED")
    a.created_at = now
    a.updated_at = now
    return a


class TestUploadAsset:
    """POST /api/v1/courses/{course_id}/modules/{module_id}/assets/upload"""

    async def test_upload_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        module_id = uuid4()
        asset_mock = _sample_asset(module_id)
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.assets.AssetService") as MockSvc:
            instance = MockSvc.return_value
            instance.upload = AsyncMock(return_value=asset_mock)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/courses/{course_id}/modules/{module_id}/assets/upload",
                    files={"file": ("notes.pdf", b"%PDF-1.4 test", "application/pdf")},
                    data={"title": "Lecture Notes"},
                )
            assert resp.status_code == 201
            body = resp.json()
            assert body["data"]["title"] == "Lecture Notes"
            assert body["data"]["asset_type"] == "pdf"

        app.dependency_overrides.clear()

    async def test_upload_forbidden_for_student(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/courses/{uuid4()}/modules/{uuid4()}/assets/upload",
                files={"file": ("notes.pdf", b"%PDF-1.4 test", "application/pdf")},
                data={"title": "Should Fail"},
            )
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestListAssets:
    """GET /api/v1/courses/{course_id}/modules/{module_id}/assets"""

    async def test_list_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        course_id = uuid4()
        module_id = uuid4()
        assets = [_sample_asset(module_id, sort_order=i) for i in range(2)]
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.assets.AssetService") as MockSvc:
            instance = MockSvc.return_value
            instance.list_for_module = AsyncMock(return_value=assets)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/courses/{course_id}/modules/{module_id}/assets"
                )
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 2

        app.dependency_overrides.clear()


class TestDownloadAsset:
    """GET /api/v1/courses/{course_id}/modules/{module_id}/assets/{asset_id}/download"""

    async def test_download_success(self, instructor, mock_session, mock_minio):
        from app.config import settings

        app = create_app()
        asset = _sample_asset(uuid4())
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.assets.AssetService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_downloadable_asset = AsyncMock(return_value=asset)
            mock_minio.presigned_get_object = AsyncMock(return_value="http://minio:9000/course-assets/presigned")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/courses/{uuid4()}/modules/{uuid4()}/assets/{uuid4()}/download"
                )
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["download_url"].startswith("http://localhost:9000/course-assets/")
            assert body["data"]["view_url"] == body["data"]["download_url"]
            assert body["data"]["expires_in"] == settings.presigned_url_ttl_seconds
            assert body["data"]["file_name"] == asset.file_name
            assert body["data"]["mime_type"] == asset.mime_type
            assert body["data"]["file_size"] == asset.file_size
            assert body["data"]["supports_inline"] is True

        app.dependency_overrides.clear()


class TestDeleteAsset:
    """DELETE /api/v1/courses/{course_id}/modules/{module_id}/assets/{asset_id}"""

    async def test_delete_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.assets.AssetService") as MockSvc:
            instance = MockSvc.return_value
            instance.delete = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    f"/api/v1/courses/{uuid4()}/modules/{uuid4()}/assets/{uuid4()}"
                )
            assert resp.status_code == 204

        app.dependency_overrides.clear()

    async def test_delete_forbidden_for_student(self, student, mock_session, mock_minio):
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(
                f"/api/v1/courses/{uuid4()}/modules/{uuid4()}/assets/{uuid4()}"
            )
        assert resp.status_code == 403

        app.dependency_overrides.clear()


class TestAssetContent:
    """GET /api/v1/courses/{course_id}/modules/{module_id}/assets/{asset_id}/content"""

    async def test_content_success(self, instructor, mock_session, mock_minio):
        app = create_app()
        asset = _sample_asset(uuid4(), file_name="lesson.md", mime_type="text/markdown", asset_type="md")
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio

        with patch("app.api.v1.assets.AssetService") as MockSvc, patch(
            "app.api.v1.assets.httpx.AsyncClient"
        ) as MockClient:
            instance = MockSvc.return_value
            instance.get_downloadable_asset = AsyncMock(return_value=asset)
            mock_minio.presigned_get_object = AsyncMock(return_value="http://minio:9000/course-assets/raw")

            client_ctx = MockClient.return_value.__aenter__.return_value
            upstream_response = MagicMock()
            upstream_response.is_error = False
            upstream_response.content = b"# lesson"
            client_ctx.get = AsyncMock(return_value=upstream_response)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/courses/{uuid4()}/modules/{uuid4()}/assets/{uuid4()}/content"
                )

            assert resp.status_code == 200
            assert resp.text == "# lesson"
            assert resp.headers["content-type"].startswith("text/markdown")
            assert resp.headers["content-disposition"].startswith("inline;")

        app.dependency_overrides.clear()
