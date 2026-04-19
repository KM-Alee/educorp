from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.services.enrollment_service import EnrollmentService


@pytest.mark.integration
async def test_capacity_enforced_under_concurrency(db_session_factory, fake_redis, monkeypatch):
    course_id = uuid4()
    course_context = {
        "course_id": str(course_id),
        "title": "Concurrency Course",
        "is_ready": True,
        "max_capacity": 1,
        "prerequisites": [],
        "modules": [],
    }

    async def fake_context(self, *, course_id):
        _ = course_id
        return course_context

    async def fake_user_summary(self, *, user_id):
        return {"full_name": f"Student {str(user_id)[:8]}"}

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

    async def enroll(student_id):
        async with db_session_factory() as session:
            service = EnrollmentService(session, fake_redis)
            try:
                result = await service.enroll(
                    student_id=student_id,
                    course_id=course_id,
                    idempotency_key=None,
                    correlation_id=str(uuid4()),
                )
                await session.commit()
                return result.enrollment.id
            except Exception:
                await session.rollback()
                return None

    student_ids = [uuid4() for _ in range(10)]
    results = await asyncio.gather(*(enroll(student_id) for student_id in student_ids))
    successes = [result for result in results if result is not None]
    assert len(successes) == 1
