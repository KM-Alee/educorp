from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.dependencies import get_current_user, get_session
from app.main import create_app
from httpx import ASGITransport, AsyncClient

from educorp_common.auth.dependencies import CurrentUser


def _make_auth(user: CurrentUser):
    async def _override():
        return user

    return _override


async def test_approve_version_signals_workflow_and_updates_approval_state() -> None:
    app = create_app()
    session = AsyncMock()
    user = CurrentUser(
        id=str(uuid4()),
        email="admin@test.com",
        roles=["admin"],
        is_active=True,
        is_verified=True,
    )

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = _make_auth(user)

    version_id = uuid4()
    version = SimpleNamespace(
        id=version_id,
        version_number=1,
        status="REVIEW_REQUIRED",
        approval_state="PENDING",
        workflow_id="publish-123",
        run_id="run-123",
    )
    approved_version = SimpleNamespace(
        id=version_id,
        version_number=1,
        status="REVIEW_REQUIRED",
        approval_state="APPROVED",
        workflow_id="publish-123",
    )

    with (
        patch("app.api.v1.versions.PublishingVersionService") as mock_service_cls,
        patch("app.api.v1.versions.Client.connect") as mock_connect,
    ):
        service = mock_service_cls.return_value
        service.get_status = AsyncMock(return_value=(version, [], []))
        service.mark_approval_requested = AsyncMock(return_value=approved_version)

        handle = AsyncMock()
        temporal = AsyncMock()
        temporal.get_workflow_handle = MagicMock(return_value=handle)
        mock_connect.return_value = temporal

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/publishing/versions/{version_id}/approve")

        assert resp.status_code == 200
        handle.signal.assert_awaited_once()
        service.mark_approval_requested.assert_awaited_once_with(
            version_id=version_id,
            approved=True,
        )
        assert resp.json()["data"]["approval_state"] == "APPROVED"

    app.dependency_overrides.clear()
