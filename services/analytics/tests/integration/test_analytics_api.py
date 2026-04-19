from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.integration
async def test_analytics_ingest_and_query(api_client, instructor_client):
    course_id = str(uuid4())
    instructor_id = "00000000-0000-0000-0000-000000000222"

    ingest = await api_client.post(
        "/api/v1/analytics/internal/events",
        json={
            "events": [
                {
                    "event_id": str(uuid4()),
                    "event_type": "user.created",
                    "aggregate_type": "user",
                    "aggregate_id": str(uuid4()),
                    "actor_id": str(uuid4()),
                    "occurred_at": "2026-04-19T00:00:00+00:00",
                    "source_service": "auth",
                    "payload": {"id": str(uuid4())},
                    "metadata": {},
                },
                {
                    "event_id": str(uuid4()),
                    "event_type": "CoursePublished",
                    "aggregate_type": "course_version",
                    "aggregate_id": str(uuid4()),
                    "actor_id": instructor_id,
                    "occurred_at": "2026-04-19T01:00:00+00:00",
                    "source_service": "publishing",
                    "payload": {
                        "course_id": course_id,
                        "course_title": "Intro to ML",
                        "instructor_id": instructor_id,
                        "version_id": str(uuid4()),
                    },
                    "metadata": {},
                },
                {
                    "event_id": str(uuid4()),
                    "event_type": "EnrollmentCreated",
                    "aggregate_type": "enrollment",
                    "aggregate_id": str(uuid4()),
                    "actor_id": str(uuid4()),
                    "occurred_at": "2026-04-19T02:00:00+00:00",
                    "source_service": "enrollment",
                    "payload": {"course_id": course_id, "course_title": "Intro to ML"},
                    "metadata": {},
                },
                {
                    "event_id": str(uuid4()),
                    "event_type": "CourseCompleted",
                    "aggregate_type": "enrollment",
                    "aggregate_id": str(uuid4()),
                    "actor_id": str(uuid4()),
                    "occurred_at": "2026-04-19T03:00:00+00:00",
                    "source_service": "progress",
                    "payload": {"course_id": course_id, "course_title": "Intro to ML"},
                    "metadata": {},
                },
                {
                    "event_id": str(uuid4()),
                    "event_type": "AssistantQueryAsked",
                    "aggregate_type": "ai_query",
                    "aggregate_id": str(uuid4()),
                    "actor_id": str(uuid4()),
                    "occurred_at": "2026-04-19T04:00:00+00:00",
                    "source_service": "ai",
                    "payload": {"course_id": course_id, "response_status": "answered"},
                    "metadata": {},
                },
            ]
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["data"] == {"processed_count": 5, "skipped_count": 0}

    platform = await api_client.get(
        "/api/v1/analytics/platform?from_date=2026-04-19&to_date=2026-04-19"
    )
    assert platform.status_code == 200
    assert platform.json()["data"] == {
        "from_date": "2026-04-19",
        "to_date": "2026-04-19",
        "total_students": 1,
        "enrollments": 1,
        "completions": 1,
        "ai_usage": 1,
        "published_courses": 1,
    }

    course = await instructor_client.get(f"/api/v1/analytics/courses/{course_id}")
    assert course.status_code == 200
    data = course.json()["data"]
    assert data["course_title"] == "Intro to ML"
    assert data["total_enrollments"] == 1
    assert data["total_completions"] == 1
    assert data["completion_rate"] == 100.0
    assert data["ai_queries"] == 1


@pytest.mark.integration
async def test_duplicate_event_is_skipped(api_client):
    event = {
        "event_id": str(uuid4()),
        "event_type": "AssistantQueryAsked",
        "aggregate_type": "ai_query",
        "aggregate_id": str(uuid4()),
        "actor_id": str(uuid4()),
        "occurred_at": "2026-04-19T04:00:00+00:00",
        "source_service": "ai",
        "payload": {"course_id": str(uuid4())},
        "metadata": {},
    }
    first = await api_client.post("/api/v1/analytics/internal/events", json={"events": [event]})
    second = await api_client.post("/api/v1/analytics/internal/events", json={"events": [event]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"] == {"processed_count": 0, "skipped_count": 1}
