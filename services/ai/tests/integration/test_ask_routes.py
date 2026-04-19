from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

from app.dependencies import get_current_user, get_kafka_producer, get_qdrant, get_redis, get_session
from app.services.qa_graph import QAService
from app.services.qa_streaming import QAStreamingService


@pytest.fixture
def override_deps(app):
    async def _session_override():
        yield object()

    async def _redis_override():
        return object()

    def _qdrant_override():
        return object()

    def _kafka_override():
        return None

    def _user_override():
        return {
            "id": str(uuid4()),
            "email": "student@example.com",
            "roles": ["student"],
            "is_active": True,
            "is_verified": True,
        }

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_qdrant] = _qdrant_override
    app.dependency_overrides[get_kafka_producer] = _kafka_override
    app.dependency_overrides[get_current_user] = _user_override

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_returns_answer(api_client, app, monkeypatch, override_deps):
    async def fake_ask(self, **kwargs):
        return {
            "query_id": uuid4(),
            "answer": "Answer [1]",
            "citations": [
                {
                    "chunk_id": "c1",
                    "module_title": "Module",
                    "asset_title": "Asset",
                    "text_snippet": "Snippet",
                    "page_number": 1,
                }
            ],
            "confidence": "high",
            "version_id": uuid4(),
            "response_type": "answer",
        }

    monkeypatch.setattr(QAService, "ask", fake_ask)

    payload = {"course_id": str(uuid4()), "question": "What is AI?", "module_id": None}
    resp = await api_client.post("/api/v1/ai/ask", json=payload)
    assert resp.status_code == 200

    body = resp.json()
    assert "data" in body
    assert body["data"]["answer"] == "Answer [1]"


@pytest.mark.asyncio
async def test_ask_stream_emits_events(api_client, app, monkeypatch, override_deps):
    async def fake_stream(self, **kwargs):
        yield {"event": "token", "data": json.dumps({"text": "Hello "})}
        yield {
            "event": "done",
            "data": json.dumps({"query_id": str(uuid4()), "confidence": "high", "total_citations": 0}),
        }

    monkeypatch.setattr(QAStreamingService, "stream", fake_stream)

    params = {"course_id": str(uuid4()), "question": "Hello?"}
    resp = await api_client.get("/api/v1/ai/ask/stream", params=params)
    assert resp.status_code == 200
    assert "event: token" in resp.text
    assert "event: done" in resp.text


@pytest.mark.asyncio
async def test_ask_clarify_returns_answer(api_client, app, monkeypatch, override_deps):
    async def fake_ask(self, **kwargs):
        return {
            "query_id": uuid4(),
            "answer": "Clarified [1]",
            "citations": [],
            "confidence": "medium",
            "version_id": uuid4(),
            "response_type": "answer",
        }

    monkeypatch.setattr(QAService, "ask", fake_ask)

    payload = {
        "course_id": str(uuid4()),
        "original_query_id": str(uuid4()),
        "clarification": "More details",
    }
    resp = await api_client.post("/api/v1/ai/ask/clarify", json=payload)
    assert resp.status_code == 200

    body = resp.json()
    assert body["data"]["answer"] == "Clarified [1]"
