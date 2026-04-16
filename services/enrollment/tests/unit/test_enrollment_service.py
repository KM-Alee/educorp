from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.models.enrollment import Enrollment
from app.schemas.enrollment import EnrollmentCreate
from app.services.enrollment_service import EnrollmentService
from educorp_common.errors import EduCorpError


class StubCourseClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def get_enrollment_context(self, *, course_id):
        _ = course_id
        return self._payload


class StubProgressClient:
    async def initialize_progress(self, **kwargs):
        _ = kwargs

    async def get_progress_summary(self, **kwargs):
        _ = kwargs
        return {"progress_percent": 0.0, "status": "NOT_STARTED"}


@pytest.mark.unit
async def test_create_enrollment_fails_when_prerequisites_missing(db_session, fake_redis, student_user):
    course_id = uuid4()
    prerequisite_id = uuid4()
    service = EnrollmentService(
        db_session,
        fake_redis,
        course_client=StubCourseClient(
            {
                "course_id": str(course_id),
                "title": "Advanced Course",
                "visibility": "PUBLISHED",
                "current_version_id": str(uuid4()),
                "max_capacity": None,
                "prerequisites": [str(prerequisite_id)],
                "modules": [],
            }
        ),
        progress_client=StubProgressClient(),
    )

    with pytest.raises(EduCorpError) as exc:
        await service.create_enrollment(
            current_user=student_user,
            payload=EnrollmentCreate(course_id=course_id),
            correlation_id=str(uuid4()),
        )

    assert exc.value.code == "ENROLLMENT_PREREQUISITES_NOT_MET"


@pytest.mark.unit
async def test_create_enrollment_returns_existing_row(db_session, fake_redis, student_user):
    course_id = uuid4()
    existing = Enrollment(
        student_id=UUID(student_user["id"]),
        course_id=course_id,
        status="ENROLLED",
    )
    db_session.add(existing)
    await db_session.commit()

    service = EnrollmentService(
        db_session,
        fake_redis,
        course_client=StubCourseClient(
            {
                "course_id": str(course_id),
                "title": "Existing Course",
                "visibility": "PUBLISHED",
                "current_version_id": str(uuid4()),
                "max_capacity": None,
                "prerequisites": [],
                "modules": [],
            }
        ),
        progress_client=StubProgressClient(),
    )

    response, idempotent_hit = await service.create_enrollment(
        current_user=student_user,
        payload=EnrollmentCreate(course_id=course_id, idempotency_key="same-key"),
        correlation_id=str(uuid4()),
    )

    assert idempotent_hit is True
    assert response.id == existing.id