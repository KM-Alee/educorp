from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_minio, get_mongo_db, get_session
from app.main import create_app
from app.schemas.common import DraftValidationIssue
from app.schemas.draft import DraftContentDocument
from educorp_common.auth.dependencies import CurrentUser


@pytest.fixture
def instructor() -> CurrentUser:
    return CurrentUser(
        id=str(uuid4()),
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


def _make_auth(user: CurrentUser):
    async def _override() -> CurrentUser:
        return user

    return _override


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_minio() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_mongo() -> MagicMock:
    return MagicMock()


class TestValidateDraft:
    async def test_validate_course_draft_success(
        self,
        instructor: CurrentUser,
        mock_session: AsyncMock,
        mock_minio: AsyncMock,
        mock_mongo: MagicMock,
    ) -> None:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio
        app.dependency_overrides[get_mongo_db] = lambda: mock_mongo

        issues = [DraftValidationIssue(field="modules", message="At least one module is required")]

        with patch("app.api.v1.courses.DraftValidationService") as mock_service:
            instance = mock_service.return_value
            instance.validate = AsyncMock(return_value=issues)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/courses/{uuid4()}/validate")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["is_valid"] is False
        assert body["data"]["issues"][0]["field"] == "modules"
        app.dependency_overrides.clear()

    async def test_validate_course_draft_requires_author_role(
        self,
        student: CurrentUser,
        mock_session: AsyncMock,
        mock_minio: AsyncMock,
        mock_mongo: MagicMock,
    ) -> None:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(student)
        app.dependency_overrides[get_minio] = lambda: mock_minio
        app.dependency_overrides[get_mongo_db] = lambda: mock_mongo

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/courses/{uuid4()}/validate")

        assert response.status_code == 403
        app.dependency_overrides.clear()


class TestDraftContent:
    async def test_get_draft_content_success(
        self,
        instructor: CurrentUser,
        mock_session: AsyncMock,
        mock_minio: AsyncMock,
        mock_mongo: MagicMock,
    ) -> None:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio
        app.dependency_overrides[get_mongo_db] = lambda: mock_mongo

        course_id = uuid4()
        document = DraftContentDocument(
            course_id=course_id,
            content={"overview": "Rich draft body", "objectives": ["Ship phase 2"]},
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.courses.DraftContentService") as mock_service:
            instance = mock_service.return_value
            instance.get = AsyncMock(return_value=document)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/courses/{course_id}/draft-content")

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["course_id"] == str(course_id)
        assert body["data"]["content"]["overview"] == "Rich draft body"
        app.dependency_overrides.clear()

    async def test_update_draft_content_success(
        self,
        instructor: CurrentUser,
        mock_session: AsyncMock,
        mock_minio: AsyncMock,
        mock_mongo: MagicMock,
    ) -> None:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[get_current_user] = _make_auth(instructor)
        app.dependency_overrides[get_minio] = lambda: mock_minio
        app.dependency_overrides[get_mongo_db] = lambda: mock_mongo

        course_id = uuid4()
        document = DraftContentDocument(
            course_id=course_id,
            content={"overview": "Updated draft body"},
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.api.v1.courses.DraftContentService") as mock_service:
            instance = mock_service.return_value
            instance.update = AsyncMock(return_value=document)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"/api/v1/courses/{course_id}/draft-content",
                    json={"content": {"overview": "Updated draft body"}},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["content"]["overview"] == "Updated draft body"
        app.dependency_overrides.clear()