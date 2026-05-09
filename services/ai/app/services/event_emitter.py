from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import structlog
from aiokafka import AIOKafkaProducer

from app.config import settings
from educorp_common.middleware.correlation import get_correlation_id

logger = structlog.get_logger()


def build_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    actor_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "correlation_id": get_correlation_id(),
        "actor_id": actor_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "payload": payload,
    }


async def emit_event(producer: AIOKafkaProducer | None, event: dict[str, Any]) -> None:
    if producer is None:
        return
    try:
        from app.dependencies import get_kafka_schema_publisher

        sr = get_kafka_schema_publisher()
        if sr is not None:
            encoded = await sr.encode_domain_event(settings.ai_usage_topic, event)
        else:
            encoded = json.dumps(event).encode("utf-8")
        await producer.send_and_wait(settings.ai_usage_topic, encoded)
    except Exception as exc:
        logger.warning("Failed to emit AI usage event", exc_info=exc)


def build_assistant_query_payload(
    *,
    query_id: UUID,
    student_id: UUID,
    course_id: UUID,
    version_id: UUID,
    question_text: str,
    chunks_retrieved: int,
    response_status: str,
    citations_count: int,
    latency_ms: int,
    tokens_used: dict[str, int],
    cached: bool,
) -> dict[str, Any]:
    return {
        "query_id": str(query_id),
        "student_id": str(student_id),
        "course_id": str(course_id),
        "version_id": str(version_id),
        "question_text": question_text,
        "chunks_retrieved": chunks_retrieved,
        "response_status": response_status,
        "citations_count": citations_count,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
        "cached": cached,
    }
