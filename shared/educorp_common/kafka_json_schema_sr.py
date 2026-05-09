from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx
import structlog

from educorp_common.events import DomainEvent

logger = structlog.get_logger()

_CONFLUENT_MAGIC = 0


def subject_for_topic(topic: str) -> str:
    """Confluent subject naming for topic values."""

    return f"{topic}-value"


def domain_event_registry_schema_str() -> str:
    """Stable JSON Schema document registered for all DomainEvent payloads."""

    schema = DomainEvent.model_json_schema(mode="serialization")
    return json.dumps(schema, separators=(",", ":"), sort_keys=True)


def encode_confluent_json_sr(schema_id: int, json_payload: bytes) -> bytes:
    """Confluent wire encoding for JSON Schema messages (magic byte + schema id + payload)."""

    return bytes([_CONFLUENT_MAGIC]) + schema_id.to_bytes(4, "big") + json_payload


def decode_kafka_json_value(value: bytes) -> dict[str, Any]:
    """Deserialize Kafka record bytes (Schema Registry JSON encoding or legacy plain JSON)."""

    if len(value) >= 5 and value[0] == _CONFLUENT_MAGIC:
        return json.loads(value[5:].decode("utf-8"))
    return json.loads(value.decode("utf-8"))


class KafkaJsonSchemaPublisher:
    """Registers DomainEvent JSON Schema per topic subject and encodes outbound payloads."""

    def __init__(self, registry_base_url: str) -> None:
        base = registry_base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=base, timeout=15.0)
        self._schema_ids: dict[str, int] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    async def ensure_topic(self, topic: str) -> None:
        subject = subject_for_topic(topic)
        if subject in self._schema_ids:
            return
        existing = await self._fetch_latest_schema_id(subject)
        if existing is not None:
            self._schema_ids[subject] = existing
            logger.info("Using existing Schema Registry subject", subject=subject, schema_id=existing)
            return
        await self._ensure_backward_config(subject)
        schema_text = domain_event_registry_schema_str()
        schema_id = await self._register_schema(subject, schema_text)
        self._schema_ids[subject] = schema_id
        logger.info("Registered Schema Registry subject", subject=subject, schema_id=schema_id)

    async def encode_domain_event(self, topic: str, payload: dict[str, Any]) -> bytes:
        subject = subject_for_topic(topic)
        if subject not in self._schema_ids:
            raise RuntimeError(f"Schema Registry subject not prepared for topic {topic!r}")
        schema_id = self._schema_ids[subject]
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return encode_confluent_json_sr(schema_id, body)

    async def _fetch_latest_schema_id(self, subject: str) -> int | None:
        encoded = quote(subject, safe="")
        response = await self._http.get(f"/subjects/{encoded}/versions/latest")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return int(data["id"])

    async def _ensure_backward_config(self, subject: str) -> None:
        encoded = quote(subject, safe="")
        response = await self._http.put(
            f"/config/{encoded}",
            json={"compatibility": "BACKWARD"},
        )
        if response.is_error:
            logger.warning(
                "Could not set Schema Registry compatibility",
                subject=subject,
                status_code=response.status_code,
                body=response.text[:500],
            )

    async def _register_schema(self, subject: str, schema_text: str) -> int:
        encoded = quote(subject, safe="")
        payload = {"schemaType": "JSON", "schema": schema_text}
        response = await self._http.post(f"/subjects/{encoded}/versions", json=payload)
        if response.is_error:
            raise RuntimeError(
                f"Schema Registry rejected schema for {subject}: "
                f"{response.status_code} {response.text[:500]}"
            )
        data = response.json()
        return int(data["id"])
