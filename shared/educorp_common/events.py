from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Normalized event envelope used across relays and consumers."""

    event_id: str
    event_type: str
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    correlation_id: str | None = None
    actor_id: str | None = None
    occurred_at: str
    version: int = 1
    source_service: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DomainEventBatch(BaseModel):
    """Batch payload for internal event ingestion endpoints."""

    events: list[DomainEvent]


class DomainEventIngestResult(BaseModel):
    """Result returned after ingesting a batch of domain events."""

    processed_count: int = 0
    skipped_count: int = 0


def normalize_event(raw: dict[str, Any]) -> DomainEvent:
    """Normalize either outbox-style or direct event payloads."""

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else None
    if payload is not None and raw.get("occurred_at") is not None:
        return DomainEvent(
            event_id=str(raw.get("event_id") or ""),
            event_type=str(raw.get("event_type") or ""),
            aggregate_type=_opt_str(raw.get("aggregate_type")),
            aggregate_id=_opt_str(raw.get("aggregate_id")),
            correlation_id=_opt_str(raw.get("correlation_id")),
            actor_id=_opt_str(raw.get("actor_id")),
            occurred_at=str(raw.get("occurred_at") or _now_iso()),
            version=int(raw.get("version") or 1),
            source_service=_opt_str(raw.get("source_service") or metadata.get("source_service")),
            payload=payload,
            metadata=metadata,
        )

    data = raw.get("data") if isinstance(raw.get("data"), dict) else payload or {}
    return DomainEvent(
        event_id=str(raw.get("event_id") or ""),
        event_type=str(raw.get("event_type") or ""),
        aggregate_type=_opt_str(raw.get("aggregate_type")),
        aggregate_id=_opt_str(raw.get("aggregate_id")),
        correlation_id=_opt_str(raw.get("correlation_id") or metadata.get("correlation_id")),
        actor_id=_opt_str(
            raw.get("actor_id")
            or metadata.get("actor_id")
            or metadata.get("user_id")
            or data.get("student_id")
            or data.get("instructor_id")
            or data.get("id")
        ),
        occurred_at=str(raw.get("timestamp") or raw.get("occurred_at") or _now_iso()),
        version=int(raw.get("version") or 1),
        source_service=_opt_str(raw.get("source_service") or metadata.get("source_service")),
        payload=data,
        metadata=metadata,
    )


def outbox_row_to_event(row: Any) -> DomainEvent:
    """Convert a transactional outbox row into a normalized event."""

    payload = row.payload if isinstance(getattr(row, "payload", None), dict) else {}
    raw = dict(payload)
    raw.setdefault("aggregate_type", _opt_str(getattr(row, "aggregate_type", None)))
    raw.setdefault("aggregate_id", _opt_str(getattr(row, "aggregate_id", None)))
    raw.setdefault("correlation_id", _opt_str(getattr(row, "correlation_id", None)))
    raw.setdefault(
        "timestamp",
        getattr(getattr(row, "created_at", None), "isoformat", lambda: _now_iso())(),
    )
    return normalize_event(raw)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
