from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_session
from app.main import create_app


@pytest.mark.integration
async def test_internal_enrollment_context_endpoint(monkeypatch):
    course_id = uuid4()

    async def fake_context(self, *, course_id):
        return {
            "course_id": course_id,
            "title": "Internal Course",
            "visibility": "PUBLISHED",
            "current_version_id": uuid4(),
            "max_capacity": 25,
            "prerequisites": [str(uuid4())],
            "modules": [
                {
                    "id": uuid4(),
                    "title": "Module A",
                    "sort_order": 0,
                    "is_required": True,
                }
            ],
        }

    monkeypatch.setattr("app.services.course_service.CourseService.get_enrollment_context", fake_context)

    app = create_app()
    app.dependency_overrides[get_session] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        response = await api_client.get(
            f"/api/v1/courses/internal/{course_id}/enrollment-context",
            headers={"X-Internal-Service-Token": "change-me"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["course_id"] == str(course_id)
    assert data["title"] == "Internal Course"
    assert data["modules"][0]["title"] == "Module A"