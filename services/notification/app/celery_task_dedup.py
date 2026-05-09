from __future__ import annotations

import os

import redis.exceptions
import structlog

logger = structlog.get_logger()

_redis_client = None


def _redis():
    global _redis_client
    if _redis_client is None:
        import redis

        url = os.environ.get("REDIS_URL", "redis://:educorp_dev@redis:6379/0")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
    return _redis_client


def reset_dedup_redis_client() -> None:
    """Test helper to clear the lazily created Redis handle."""

    global _redis_client
    _redis_client = None


def _done_key(task_name: str, celery_task_id: str) -> str:
    return f"notifications:celery:done:v1:{task_name}:{celery_task_id}"


def should_skip_completed(task_name: str, celery_task_id: str | None) -> bool:
    """Return True when this Celery task id was already completed successfully."""

    if not celery_task_id:
        return False
    try:
        return bool(_redis().exists(_done_key(task_name, celery_task_id)))
    except redis.exceptions.RedisError:
        logger.warning("celery_dedup_redis_error", task_name=task_name)
        return False


def mark_completed(task_name: str, celery_task_id: str | None) -> None:
    """Persist completion so retries after a successful send do not duplicate work."""

    if not celery_task_id:
        return
    try:
        _redis().set(_done_key(task_name, celery_task_id), "1", ex=86400 * 7)
    except redis.exceptions.RedisError:
        logger.warning("celery_dedup_mark_failed", task_name=task_name)
