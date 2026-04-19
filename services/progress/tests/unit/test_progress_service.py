from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.schemas.internal import ProgressInitRequest
from app.services.progress_service import ProgressService


@pytest.mark.unit
async def test_progress_completion_creates_certificate(db_session, student_user, monkeypatch):
    enrollment_id = uuid4()
    course_id = uuid4()
    first_module_id = uuid4()
    second_module_id = uuid4()
    seen_completion: dict[str, object] = {}

    await db_session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS enrollment.enrollments (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                status TEXT NOT NULL,
                completed_at TEXT,
                updated_at TEXT
            )
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO enrollment.enrollments (id, student_id, course_id, status)
            VALUES (:id, :student_id, :course_id, 'ENROLLED')
            """
        ),
        {
            "id": str(enrollment_id),
            "student_id": str(student_user["id"]),
            "course_id": str(course_id),
        },
    )

    async def fake_mark_completed(self, **kwargs):
        seen_completion.update(kwargs)

    monkeypatch.setattr(
        "app.services.progress_service.EnrollmentClient.mark_completed",
        fake_mark_completed,
    )

    service = ProgressService(db_session)
    await service.initialize_progress(
        payload=ProgressInitRequest(
            enrollment_id=enrollment_id,
            student_id=UUID(student_user["id"]),
            student_name="Student Example",
            course_id=course_id,
            course_title="Progress Course",
            modules=[
                {"id": first_module_id, "title": "One", "sort_order": 0, "is_required": True},
                {"id": second_module_id, "title": "Two", "sort_order": 1, "is_required": True},
            ],
            enrolled_at="2026-04-16T00:00:00Z",
        ),
        correlation_id=str(uuid4()),
    )

    first = await service.complete_module(
        enrollment_id=enrollment_id,
        module_id=first_module_id,
        student_id=UUID(student_user["id"]),
        correlation_id=str(uuid4()),
    )
    assert first.overall_progress_percent == 50.0
    assert first.course_completed is False

    second = await service.complete_module(
        enrollment_id=enrollment_id,
        module_id=second_module_id,
        student_id=UUID(student_user["id"]),
        correlation_id=str(uuid4()),
    )
    assert second.overall_progress_percent == 100.0
    assert second.course_completed is True
    assert second.certificate is not None
    assert second.certificate.certificate_number.startswith("SC-")
    assert seen_completion["enrollment_id"] == enrollment_id
