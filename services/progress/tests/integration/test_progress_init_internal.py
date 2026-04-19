from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.integration
async def test_internal_progress_init_is_idempotent(api_client, student_user):
    enrollment_id = uuid4()
    payload = {
        "enrollment_id": str(enrollment_id),
        "student_id": student_user["id"],
        "student_name": "Student Example",
        "course_id": str(uuid4()),
        "course_title": "Internal Init",
        "modules": [{"id": str(uuid4()), "title": "Intro", "sort_order": 0, "is_required": True}],
        "enrolled_at": "2026-04-16T00:00:00Z",
    }
    headers = {"X-Internal-Service-Token": "change-me"}

    first = await api_client.post("/api/v1/progress/internal/init", json=payload, headers=headers)
    second = await api_client.post("/api/v1/progress/internal/init", json=payload, headers=headers)

    assert first.status_code == 201
    assert first.json()["data"]["initialized"] is True
    assert second.status_code == 201
    assert second.json()["data"]["initialized"] is False
