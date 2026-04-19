from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.models.enrollment import Enrollment
from app.models.enrollment_audit import EnrollmentAudit
from app.models.outbox import OutboxEvent
from app.services.enrollment_service import EnrollmentService
from educorp_common.errors import EduCorpError


@pytest.mark.unit
async def test_enroll_fails_when_prerequisites_missing(
    db_session, fake_redis, student_user, monkeypatch
):
    course_id = uuid4()
    prerequisite_id = uuid4()

    async def fake_course_context(self, *, course_id):
        _ = course_id
        return {
            "course_id": str(course_id),
            "title": "Advanced Course",
            "is_ready": True,
            "max_capacity": None,
            "prerequisites": [str(prerequisite_id)],
            "modules": [],
        }

    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {"full_name": "Student Example"}

    monkeypatch.setattr(
        "app.services.enrollment_service.CourseClient.get_enrollment_context",
        fake_course_context,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.AuthClient.get_user_summary",
        fake_user_summary,
    )

    service = EnrollmentService(db_session, fake_redis)

    with pytest.raises(EduCorpError) as exc:
        await service.enroll(
            student_id=UUID(student_user["id"]),
            course_id=course_id,
            idempotency_key="idem-prereq",
            correlation_id=str(uuid4()),
        )

    assert exc.value.code == "ENROLLMENT_PREREQUISITES_NOT_MET"


@pytest.mark.unit
async def test_enroll_returns_existing_row_for_same_student_course(
    db_session, fake_redis, student_user
):
    course_id = uuid4()
    existing = Enrollment(
        student_id=UUID(student_user["id"]),
        course_id=course_id,
        status="ENROLLED",
        idempotency_key="existing-key",
    )
    db_session.add(existing)
    await db_session.commit()

    service = EnrollmentService(db_session, fake_redis)
    result = await service.enroll(
        student_id=UUID(student_user["id"]),
        course_id=course_id,
        idempotency_key="new-key",
        correlation_id=str(uuid4()),
    )

    assert result.idempotent_hit is True
    assert result.enrollment.id == existing.id


@pytest.mark.unit
async def test_enroll_persists_progress_init_audits_and_outbox(
    db_session, fake_redis, student_user, monkeypatch
):
    course_id = uuid4()
    module_id = uuid4()
    seen_progress: dict[str, object] = {}

    async def fake_course_context(self, *, course_id):
        _ = course_id
        return {
            "course_id": str(course_id),
            "title": "Ready Course",
            "is_ready": True,
            "max_capacity": None,
            "prerequisites": [],
            "modules": [
                {
                    "id": str(module_id),
                    "title": "Module One",
                    "sort_order": 0,
                    "is_required": True,
                }
            ],
        }

    async def fake_user_summary(self, *, user_id):
        _ = user_id
        return {"full_name": "Student Example"}

    async def fake_initialize_progress(self, **kwargs):
        seen_progress.update(kwargs)

    monkeypatch.setattr(
        "app.services.enrollment_service.CourseClient.get_enrollment_context",
        fake_course_context,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.AuthClient.get_user_summary",
        fake_user_summary,
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.ProgressClient.initialize_progress",
        fake_initialize_progress,
    )

    service = EnrollmentService(db_session, fake_redis)
    result = await service.enroll(
        student_id=UUID(student_user["id"]),
        course_id=course_id,
        idempotency_key="idem-happy",
        correlation_id=str(uuid4()),
    )
    await db_session.commit()

    assert result.idempotent_hit is False
    assert seen_progress["enrollment_id"] == result.enrollment.id
    assert seen_progress["student_name"] == "Student Example"

    persisted = await db_session.scalar(
        select(Enrollment).where(Enrollment.id == result.enrollment.id)
    )
    assert persisted is not None
    assert persisted.status == "ENROLLED"

    audits = (
        (
            await db_session.execute(
                select(EnrollmentAudit).where(EnrollmentAudit.enrollment_id == result.enrollment.id)
            )
        )
        .scalars()
        .all()
    )
    assert [audit.action for audit in audits] == [
        "PREREQUISITE_CHECK",
        "CAPACITY_CHECK",
        "ENROLLED",
    ]

    outbox = (
        await db_session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == result.enrollment.id)
        )
    ).scalar_one_or_none()
    assert outbox is not None
    assert outbox.event_type == "EnrollmentCreated"
