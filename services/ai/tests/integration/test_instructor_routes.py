from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.dependencies import (
    get_current_user,
    get_kafka_producer,
    get_mongo_db,
    get_qdrant,
    get_redis,
    get_session,
)


class _FakeMongoDatabase:
    def __getitem__(self, _name: str):
        return object()


@pytest.fixture
def override_instructor_deps(app):
    async def _session_override():
        yield object()

    async def _redis_override():
        return object()

    def _qdrant_override():
        return object()

    def _mongo_override():
        return _FakeMongoDatabase()

    def _kafka_override():
        return None

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_qdrant] = _qdrant_override
    app.dependency_overrides[get_mongo_db] = _mongo_override
    app.dependency_overrides[get_kafka_producer] = _kafka_override

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_instructor_route_allows_instructor(
    api_client, app, monkeypatch, override_instructor_deps
):
    async def _user_override():
        return {
            "id": str(uuid4()),
            "email": "instructor@example.com",
            "roles": ["instructor"],
            "is_active": True,
            "is_verified": True,
        }

    async def fake_enqueue_job(self, **kwargs):
        _ = kwargs

    app.dependency_overrides[get_current_user] = _user_override
    monkeypatch.setattr(
        "app.services.instructor_service.InstructorService.enqueue_job", fake_enqueue_job
    )

    response = await api_client.post(
        "/api/v1/ai/instructor/enhance",
        json={
            "course_id": str(uuid4()),
            "job_type": "summary",
            "scope": "course",
            "parameters": {},
        },
    )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_instructor_route_allows_admin(
    api_client, app, monkeypatch, override_instructor_deps
):
    async def _user_override():
        return {
            "id": str(uuid4()),
            "email": "admin@example.com",
            "roles": ["admin"],
            "is_active": True,
            "is_verified": True,
        }

    async def fake_enqueue_job(self, **kwargs):
        _ = kwargs

    app.dependency_overrides[get_current_user] = _user_override
    monkeypatch.setattr(
        "app.services.instructor_service.InstructorService.enqueue_job", fake_enqueue_job
    )

    response = await api_client.post(
        "/api/v1/ai/instructor/enhance",
        json={
            "course_id": str(uuid4()),
            "job_type": "summary",
            "scope": "course",
            "parameters": {},
        },
    )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_instructor_route_rejects_student(api_client, app, override_instructor_deps):
    async def _user_override():
        return {
            "id": str(uuid4()),
            "email": "student@example.com",
            "roles": ["student"],
            "is_active": True,
            "is_verified": True,
        }

    app.dependency_overrides[get_current_user] = _user_override

    response = await api_client.post(
        "/api/v1/ai/instructor/enhance",
        json={
            "course_id": str(uuid4()),
            "job_type": "summary",
            "scope": "course",
            "parameters": {},
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_instructor_route_rejects_module_scope_without_module_id(
    api_client, app, override_instructor_deps
):
    async def _user_override():
        return {
            "id": str(uuid4()),
            "email": "instructor@example.com",
            "roles": ["instructor"],
            "is_active": True,
            "is_verified": True,
        }

    app.dependency_overrides[get_current_user] = _user_override

    response = await api_client.post(
        "/api/v1/ai/instructor/enhance",
        json={
            "course_id": str(uuid4()),
            "job_type": "summary",
            "scope": "module",
            "parameters": {},
        },
    )

    assert response.status_code == 422
    assert "module_id" in response.text


@pytest.mark.asyncio
async def test_get_job_returns_rich_status_fields(
    api_client, app, monkeypatch, override_instructor_deps
):
    async def _user_override():
        return {
            "id": str(uuid4()),
            "email": "admin@example.com",
            "roles": ["admin"],
            "is_active": True,
            "is_verified": True,
        }

    created_at = datetime.now(timezone.utc)
    started_at = datetime.now(timezone.utc)
    completed_at = datetime.now(timezone.utc)
    job_id = uuid4()

    async def fake_get_job(self, _job_id: str):
        return {
            "job_id": str(job_id),
            "job_type": "summary",
            "status": "FAILED",
            "input": {"scope": "course", "module_id": None, "parameters": {}},
            "result": None,
            "created_at": created_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "error": {"code": "AI_PROVIDER_ERROR", "message": "boom", "retryable": False},
            "course_id": str(uuid4()),
        }

    app.dependency_overrides[get_current_user] = _user_override
    monkeypatch.setattr(
        "app.repositories.ai_jobs_repository.AiJobsRepository.get_job", fake_get_job
    )

    response = await api_client.get(f"/api/v1/ai/instructor/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "FAILED"
    assert body["input"]["scope"] == "course"
    assert body["started_at"] is not None
    assert body["error"]["code"] == "AI_PROVIDER_ERROR"


@pytest.mark.asyncio
async def test_list_jobs_returns_input_metadata(
    api_client, app, monkeypatch, override_instructor_deps
):
    user_id = str(uuid4())

    async def _user_override():
        return {
            "id": user_id,
            "email": "admin@example.com",
            "roles": ["admin"],
            "is_active": True,
            "is_verified": True,
        }

    async def fake_list_jobs(self, *, filters, page: int, page_size: int):
        assert filters["requested_by"] == user_id
        assert page == 1
        assert page_size == 20
        return (
            [
                {
                    "job_id": str(uuid4()),
                    "job_type": "summary",
                    "status": "QUEUED",
                    "input": {"scope": "course", "module_id": None, "parameters": {}},
                    "created_at": datetime.now(timezone.utc),
                }
            ],
            1,
        )

    app.dependency_overrides[get_current_user] = _user_override
    monkeypatch.setattr(
        "app.repositories.ai_jobs_repository.AiJobsRepository.list_jobs", fake_list_jobs
    )

    response = await api_client.get("/api/v1/ai/instructor/jobs")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["input"]["scope"] == "course"
