from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from app.config import settings


def normalize_question(question: str) -> str:
    return " ".join(question.lower().strip().split())


def question_cache_key(
    question: str,
    course_id: str,
    version_id: str,
    module_id: str | None = None,
    asset_id: str | None = None,
) -> str:
    normalized = normalize_question(question)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    module_scope = module_id or "*"
    asset_scope = asset_id or "*"
    return f"cache:ai:{digest}:{course_id}:{version_id}:{module_scope}:{asset_scope}"


async def get_cached_response(
    redis: Redis,
    *,
    question: str,
    course_id: str,
    version_id: str,
    module_id: str | None = None,
    asset_id: str | None = None,
) -> dict[str, Any] | None:
    key = question_cache_key(question, course_id, version_id, module_id, asset_id)
    raw = await redis.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_cached_response(
    redis: Redis,
    *,
    question: str,
    course_id: str,
    version_id: str,
    module_id: str | None = None,
    asset_id: str | None = None,
    payload: dict[str, Any],
    ttl_seconds: int | None = None,
) -> None:
    key = question_cache_key(question, course_id, version_id, module_id, asset_id)
    ttl = ttl_seconds or settings.ai_cache_ttl_seconds
    await redis.setex(key, ttl, json.dumps(payload))
