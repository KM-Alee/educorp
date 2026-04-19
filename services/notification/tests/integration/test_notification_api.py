from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.integration
async def test_ingest_notifications_preferences_and_read_flow(
    api_client, monkeypatch, student_user
):
    sent_emails: list[dict[str, str]] = []

    class DummyDelay:
        @staticmethod
        def delay(**kwargs):
            sent_emails.append(kwargs)

    async def fake_user_summary(self, *, user_id):
        assert str(user_id) == student_user["id"]
        return {
            "id": student_user["id"],
            "email": student_user["email"],
            "first_name": "Student",
            "last_name": "Example",
            "full_name": "Student Example",
            "roles": ["student"],
        }

    monkeypatch.setattr("app.services.notification_service.send_email_task", DummyDelay())
    monkeypatch.setattr(
        "app.services.notification_service.AuthClient.get_user_summary",
        fake_user_summary,
    )

    event_id = str(uuid4())
    ingest = await api_client.post(
        "/api/v1/notifications/internal/events",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "event_type": "EnrollmentCreated",
                    "aggregate_type": "enrollment",
                    "aggregate_id": str(uuid4()),
                    "actor_id": student_user["id"],
                    "occurred_at": "2026-04-19T00:00:00+00:00",
                    "source_service": "enrollment",
                    "payload": {
                        "student_id": student_user["id"],
                        "course_id": str(uuid4()),
                        "course_title": "Intro to ML",
                    },
                    "metadata": {},
                }
            ]
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["data"] == {"processed_count": 1, "skipped_count": 0}

    listing = await api_client.get("/api/v1/notifications/")
    assert listing.status_code == 200
    notifications = listing.json()["data"]
    assert len(notifications) == 1
    assert notifications[0]["type"] == "enrollment_confirmed"
    assert notifications[0]["metadata"]["event_type"] == "EnrollmentCreated"
    assert len(sent_emails) == 1

    prefs = await api_client.patch(
        "/api/v1/notifications/preferences",
        json={"enrollment_confirmed_email": False},
    )
    assert prefs.status_code == 200
    assert prefs.json()["data"]["enrollment_confirmed_email"] is False

    second = await api_client.post(
        "/api/v1/notifications/internal/events",
        json={
            "events": [
                {
                    "event_id": str(uuid4()),
                    "event_type": "EnrollmentCreated",
                    "aggregate_type": "enrollment",
                    "aggregate_id": str(uuid4()),
                    "actor_id": student_user["id"],
                    "occurred_at": "2026-04-19T01:00:00+00:00",
                    "source_service": "enrollment",
                    "payload": {
                        "student_id": student_user["id"],
                        "course_id": str(uuid4()),
                        "course_title": "Advanced ML",
                    },
                    "metadata": {},
                }
            ]
        },
    )
    assert second.status_code == 200
    assert len(sent_emails) == 1

    unread = await api_client.get("/api/v1/notifications/?is_read=false")
    assert unread.status_code == 200
    assert len(unread.json()["data"]) == 2

    first_notification_id = notifications[0]["id"]
    mark_read = await api_client.patch(f"/api/v1/notifications/{first_notification_id}/read")
    assert mark_read.status_code == 200
    assert mark_read.json()["data"]["is_read"] is True

    read_all = await api_client.post("/api/v1/notifications/read-all")
    assert read_all.status_code == 200
    assert read_all.json()["data"]["updated_count"] == 1


@pytest.mark.integration
async def test_ingest_duplicate_event_is_idempotent(api_client, monkeypatch, student_user):
    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {
            "id": student_user["id"],
            "email": student_user["email"],
            "first_name": "Student",
            "last_name": "Example",
            "full_name": "Student Example",
        }

    monkeypatch.setattr(
        "app.services.notification_service.AuthClient.get_user_summary",
        fake_user_summary,
    )
    monkeypatch.setattr(
        "app.services.notification_service.send_email_task",
        type("X", (), {"delay": staticmethod(lambda **_kwargs: None)})(),
    )

    event = {
        "event_id": str(uuid4()),
        "event_type": "CourseCompleted",
        "aggregate_type": "enrollment",
        "aggregate_id": str(uuid4()),
        "actor_id": student_user["id"],
        "occurred_at": "2026-04-19T00:00:00+00:00",
        "source_service": "progress",
        "payload": {
            "student_id": student_user["id"],
            "course_id": str(uuid4()),
            "course_title": "Intro to ML",
            "certificate_number": "SC-2026-12345",
        },
        "metadata": {},
    }

    first = await api_client.post("/api/v1/notifications/internal/events", json={"events": [event]})
    second = await api_client.post(
        "/api/v1/notifications/internal/events", json={"events": [event]}
    )
    assert first.status_code == 200
    assert second.status_code == 200

    listing = await api_client.get("/api/v1/notifications/")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
