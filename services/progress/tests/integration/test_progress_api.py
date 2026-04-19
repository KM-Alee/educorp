from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_progress_detail_completion_dashboard_and_certificate(
    api_client, db_session, monkeypatch, student_user
):
    async def fake_mark_completed(self, **kwargs):
        _ = kwargs

    monkeypatch.setattr(
        "app.services.progress_service.EnrollmentClient.mark_completed",
        fake_mark_completed,
    )

    enrollment_id = uuid4()
    course_id = uuid4()
    module_ids = [uuid4(), uuid4()]
    headers = {"X-Internal-Service-Token": "change-me"}

    await db_session.execute(
        text(
            """
            INSERT INTO enrollment.enrollments (id, student_id, course_id, status)
            VALUES (:id, :student_id, :course_id, 'ENROLLED')
            """
        ),
        {
            "id": str(enrollment_id),
            "student_id": student_user["id"],
            "course_id": str(course_id),
        },
    )
    await db_session.commit()

    init_response = await api_client.post(
        "/api/v1/progress/internal/init",
        json={
            "enrollment_id": str(enrollment_id),
            "student_id": student_user["id"],
            "student_name": "Student Example",
            "course_id": str(course_id),
            "course_title": "Dashboard Course",
            "modules": [
                {"id": str(module_ids[0]), "title": "Part 1", "sort_order": 0, "is_required": True},
                {"id": str(module_ids[1]), "title": "Part 2", "sort_order": 1, "is_required": True},
            ],
            "enrolled_at": "2026-04-16T00:00:00Z",
        },
        headers=headers,
    )
    assert init_response.status_code == 201

    detail = await api_client.get(f"/api/v1/progress/enrollments/{enrollment_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["progress_percent"] == 0.0
    assert len(detail.json()["data"]["modules"]) == 2

    first_completion = await api_client.post(
        f"/api/v1/progress/enrollments/{enrollment_id}/modules/{module_ids[0]}/complete"
    )
    assert first_completion.status_code == 200
    assert first_completion.json()["data"]["overall_progress_percent"] == 50.0

    second_completion = await api_client.post(
        f"/api/v1/progress/enrollments/{enrollment_id}/modules/{module_ids[1]}/complete"
    )
    assert second_completion.status_code == 200
    assert second_completion.json()["data"]["course_completed"] is True
    certificate = second_completion.json()["data"]["certificate"]
    assert certificate is not None

    dashboard = await api_client.get("/api/v1/progress/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["completed_courses"] == 1
    assert dashboard.json()["data"]["total_certificates"] == 1

    certificates = await api_client.get("/api/v1/progress/certificates")
    assert certificates.status_code == 200
    assert len(certificates.json()["data"]) == 1

    certificate_detail = await api_client.get(f"/api/v1/progress/certificates/{certificate['id']}")
    assert certificate_detail.status_code == 200
    assert (
        certificate_detail.json()["data"]["certificate_number"] == certificate["certificate_number"]
    )
