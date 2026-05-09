from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def test_should_skip_completed_when_redis_reports_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.celery_task_dedup import reset_dedup_redis_client, should_skip_completed

    reset_dedup_redis_client()
    fake = MagicMock()
    fake.exists.return_value = True
    monkeypatch.setattr("app.celery_task_dedup._redis_client", fake)
    assert should_skip_completed("send_email", "task-123") is True


def test_send_email_task_returns_duplicate_when_dedup_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import tasks

    monkeypatch.setattr(tasks, "should_skip_completed", lambda *_a, **_k: True)
    result = tasks.send_email_task.run("learner@example.com", "Hello", "Body")
    assert result["status"] == "duplicate_skipped"
