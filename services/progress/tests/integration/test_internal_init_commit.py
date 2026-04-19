from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.student_progress import StudentProgress


@pytest.mark.integration
async def test_internal_progress_init_commits_rows(db_session_factory, app, student_user):
    enrollment_id = uuid4()

    from app.dependencies import get_session
    from httpx import ASGITransport, AsyncClient

    async def override_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/progress/internal/init",
            json={
                "enrollment_id": str(enrollment_id),
                "student_id": student_user["id"],
                "student_name": "Student Example",
                "course_id": str(uuid4()),
                "course_title": "Internal Init",
                "modules": [
                    {"id": str(uuid4()), "title": "Intro", "sort_order": 0, "is_required": True}
                ],
                "enrolled_at": "2026-04-16T00:00:00Z",
            },
            headers={"X-Internal-Service-Token": "change-me"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201

    async with db_session_factory() as session:
        persisted = await session.scalar(
            select(StudentProgress).where(StudentProgress.enrollment_id == enrollment_id)
        )
        assert persisted is not None
        assert persisted.status == "NOT_STARTED"
