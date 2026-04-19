from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.enrollment import Enrollment


@pytest.mark.integration
async def test_internal_completion_commits_persisted_status(db_session_factory, app, fake_redis):
    student_id = uuid4()
    course_id = uuid4()
    enrollment_id = uuid4()

    async with db_session_factory() as session:
        session.add(
            Enrollment(
                id=enrollment_id,
                student_id=student_id,
                course_id=course_id,
                status="ENROLLED",
            )
        )
        await session.commit()

    from app.dependencies import get_redis, get_session
    from httpx import ASGITransport, AsyncClient

    async def override_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/enrollments/internal/enrollments/{enrollment_id}/complete",
            json={"completed_at": datetime.now(timezone.utc).isoformat()},
            headers={"X-Internal-Service-Token": "change-me"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    async with db_session_factory() as session:
        persisted = await session.scalar(select(Enrollment).where(Enrollment.id == enrollment_id))
        assert persisted is not None
        assert persisted.status == "COMPLETED"
        assert persisted.completed_at is not None
