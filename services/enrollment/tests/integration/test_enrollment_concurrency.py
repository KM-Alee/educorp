from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from app.schemas.enrollment import EnrollmentCreate
from app.services.enrollment_service import EnrollmentService
from educorp_common.auth.dependencies import CurrentUser


class StubCourseClient:
    def __init__(self, course_context: dict) -> None:
        self._course_context = course_context

    async def get_enrollment_context(self, *, course_id):
        _ = course_id
        return self._course_context


class StubProgressClient:
    async def initialize_progress(self, **kwargs):
        _ = kwargs

    async def get_progress_summary(self, **kwargs):
        _ = kwargs
        return {"progress_percent": 0.0, "status": "NOT_STARTED"}


@pytest.mark.integration
async def test_capacity_enforced_under_concurrency(db_session_factory, fake_redis):
    course_id = uuid4()
    course_context = {
        "course_id": str(course_id),
        "title": "Concurrency Course",
        "visibility": "PUBLISHED",
        "current_version_id": str(uuid4()),
        "max_capacity": 1,
        "prerequisites": [],
        "modules": [],
    }

    async def enroll(user: CurrentUser):
        async with db_session_factory() as session:
            service = EnrollmentService(
                session,
                fake_redis,
                course_client=StubCourseClient(course_context),
                progress_client=StubProgressClient(),
            )
            try:
                response, _ = await service.create_enrollment(
                    current_user=user,
                    payload=EnrollmentCreate(course_id=UUID(course_context["course_id"])),
                    correlation_id=str(uuid4()),
                )
                return response.id
            except Exception:
                return None

    users = [
        CurrentUser(
            id=str(uuid4()),
            email=f"student-{index}@test.com",
            roles=["student"],
            is_active=True,
            is_verified=True,
        )
        for index in range(10)
    ]

    results = await asyncio.gather(*(enroll(user) for user in users))
    successes = [result for result in results if result is not None]
    assert len(successes) == 1