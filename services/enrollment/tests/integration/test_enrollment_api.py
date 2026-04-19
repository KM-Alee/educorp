from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.fixture
def ready_course_context():
    course_id = uuid4()
    return {
        "course_id": str(course_id),
        "title": "Intro to ML",
        "is_ready": True,
        "max_capacity": 10,
        "prerequisites": [],
        "modules": [
            {
                "id": str(uuid4()),
                "title": "Introduction",
                "sort_order": 0,
                "is_required": True,
            }
        ],
    }


@pytest.mark.integration
async def test_enrollment_happy_path_and_status(api_client, monkeypatch, ready_course_context):
    async def fake_context(self, *, course_id):
        _ = course_id
        return ready_course_context

    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {"full_name": "Student Example"}

    async def fake_init(self, **kwargs):
        _ = kwargs

    async def fake_summary(self, **kwargs):
        _ = kwargs
        return {"progress_percent": 0.0, "status": "NOT_STARTED"}

    async def fake_cancel(self, **kwargs):
        _ = kwargs
        return {"progress_percent": 0.0, "status": "CANCELLED"}

    monkeypatch.setattr(
        "app.services.enrollment_service.CourseClient.get_enrollment_context",
        fake_context,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.AuthClient.get_user_summary",
        fake_user_summary,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.ProgressClient.initialize_progress",
        fake_init,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.ProgressClient.get_progress_summary",
        fake_summary,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.ProgressClient.cancel_progress",
        fake_cancel,
    )

    response = await api_client.post(
        "/api/v1/enrollments/",
        json={"course_id": ready_course_context["course_id"], "idempotency_key": "idem-1"},
    )
    assert response.status_code == 201
    enrollment_id = response.json()["data"]["id"]

    detail = await api_client.get(f"/api/v1/enrollments/{enrollment_id}")
    assert detail.status_code == 200

    listing = await api_client.get("/api/v1/enrollments/")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    status_resp = await api_client.get(
        f"/api/v1/enrollments/courses/{ready_course_context['course_id']}/enrollment-status"
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["is_enrolled"] is True
    assert status_resp.json()["data"]["progress_percent"] == 0.0

    cancel = await api_client.post(f"/api/v1/enrollments/{enrollment_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["data"]["status"] == "CANCELLED"


@pytest.mark.integration
async def test_enrollment_idempotent_replay_returns_200(
    api_client, monkeypatch, ready_course_context
):
    async def fake_context(self, *, course_id):
        _ = course_id
        return ready_course_context

    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {"full_name": "Student Example"}

    async def fake_init(self, **kwargs):
        _ = kwargs

    monkeypatch.setattr(
        "app.services.enrollment_service.CourseClient.get_enrollment_context",
        fake_context,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.AuthClient.get_user_summary",
        fake_user_summary,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.ProgressClient.initialize_progress",
        fake_init,
    )

    payload = {"course_id": ready_course_context["course_id"], "idempotency_key": "idem-repeat"}
    first = await api_client.post("/api/v1/enrollments/", json=payload)
    second = await api_client.post("/api/v1/enrollments/", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


@pytest.mark.integration
async def test_enrollment_rejects_missing_prerequisite(
    api_client, monkeypatch, ready_course_context
):
    ready_course_context["prerequisites"] = [str(uuid4())]

    async def fake_context(self, *, course_id):
        _ = course_id
        return ready_course_context

    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {"full_name": "Student Example"}

    monkeypatch.setattr(
        "app.services.enrollment_service.CourseClient.get_enrollment_context",
        fake_context,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.AuthClient.get_user_summary",
        fake_user_summary,
    )

    response = await api_client.post(
        "/api/v1/enrollments/",
        json={"course_id": ready_course_context["course_id"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ENROLLMENT_PREREQUISITES_NOT_MET"
