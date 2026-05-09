from __future__ import annotations

import json
from pathlib import Path

import pytest

from educorp_common.circuit_breaker import AsyncCircuitBreaker
from educorp_common.errors import CircuitBreakerOpenError
from educorp_common.kafka_json_schema_sr import (
    decode_kafka_json_value,
    domain_event_registry_schema_str,
    encode_confluent_json_sr,
)


def test_decode_kafka_json_legacy_plain_json_roundtrip() -> None:
    payload = {"event_id": "e1", "event_type": "EnrollmentCreated", "data": {"x": 1}}
    raw = json.dumps(payload).encode("utf-8")
    assert decode_kafka_json_value(raw) == payload


def test_decode_kafka_json_confluent_wrapped() -> None:
    payload = {"event_id": "e2", "event_type": "CoursePublished"}
    body = json.dumps(payload).encode("utf-8")
    wrapped = encode_confluent_json_sr(99, body)
    assert decode_kafka_json_value(wrapped) == payload


def test_domain_event_registry_schema_is_valid_json() -> None:
    schema_text = domain_event_registry_schema_str()
    parsed = json.loads(schema_text)
    assert parsed.get("type") == "object"


@pytest.mark.asyncio
async def test_async_circuit_breaker_opens_after_failures() -> None:
    breaker = AsyncCircuitBreaker(fail_max=2, reset_timeout_seconds=60.0)

    async def boom() -> None:
        raise ConnectionError("upstream")

    with pytest.raises(ConnectionError):
        await breaker.call(boom)
    with pytest.raises(ConnectionError):
        await breaker.call(boom)
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(boom)


def test_traefik_dynamic_lists_rate_limit_and_parameterized_cors() -> None:
    path = Path(__file__).resolve().parents[2] / "infra" / "traefik" / "dynamic" / "services.yml"
    text = path.read_text(encoding="utf-8")
    assert "rate-limit" in text
    assert text.count("- rate-limit") >= 9
    assert "TRAEFIK_CORS_ORIGIN_1" in text
