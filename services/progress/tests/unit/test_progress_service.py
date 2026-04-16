from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.schemas.internal import ProgressInitRequest
from app.services.progress_service import ProgressService


class StubEnrollmentClient:
    async def mark_completed(self, **kwargs):
        _ = kwargs


@pytest.mark.unit
async def test_progress_completion_creates_certificate(db_session, student_user):
    service = ProgressService(db_session, enrollment_client=StubEnrollmentClient())
    enrollment_id = uuid4()
    first_module_id = uuid4()
    second_module_id = uuid4()

    await service.initialize_progress(
        payload=ProgressInitRequest(
            enrollment_id=enrollment_id,
            student_id=UUID(student_user["id"]),
            course_id=uuid4(),
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
        current_user=student_user,
        enrollment_id=enrollment_id,
        module_id=first_module_id,
        correlation_id=str(uuid4()),
    )
    assert first.overall_progress_percent == 50.0
    assert first.course_completed is False

    second = await service.complete_module(
        current_user=student_user,
        enrollment_id=enrollment_id,
        module_id=second_module_id,
        correlation_id=str(uuid4()),
    )
    assert second.overall_progress_percent == 100.0
    assert second.course_completed is True
    assert second.certificate is not None
    assert second.certificate.certificate_number.startswith("SC-")