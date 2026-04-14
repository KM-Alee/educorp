---
applyTo: "services/*/app/events/**/*.py,services/*/app/services/**/*outbox*,infra/kafka/**"
---

# Kafka & Event Conventions

## Event Envelope
All events follow this format:
```python
{
    "event_type": "course.published",
    "event_id": "uuid-v4",
    "timestamp": "2026-04-11T10:30:00Z",
    "data": { ... },
    "metadata": {
        "correlation_id": "uuid-from-request",
        "source_service": "publishing",
        "user_id": "uuid"
    }
}
```

## Topic Naming
- Pattern: `<domain>.lifecycle` (e.g., `course.lifecycle`, `user.lifecycle`)
- DLQ: `<domain>.lifecycle.dlq`
- Consumer group: `<service>-consumers`

## Topics
| Topic | Producer | Consumers |
|-------|----------|-----------|
| `user.lifecycle` | auth | notification, analytics |
| `course.lifecycle` | course, publishing | search, notification, analytics, ai |
| `enrollment.lifecycle` | enrollment | progress, notification, analytics |
| `progress.lifecycle` | progress | notification, analytics |
| `ai.lifecycle` | ai | analytics |
| `notification.lifecycle` | notification | analytics |

## Transactional Outbox Pattern
**Never produce to Kafka directly from a request handler.**

1. Write the event to `shared.outbox_events` in the same DB transaction as the business operation
2. A background relay process reads unpublished events and produces to Kafka
3. Mark events as published after successful produce

```python
class OutboxRepository:
    async def write(self, event_type: str, data: dict, metadata: dict | None = None):
        event = OutboxEvent(
            event_type=event_type,
            event_id=uuid4(),
            payload={"event_type": event_type, "data": data, "metadata": metadata},
        )
        self._session.add(event)
```

## Consumer Rules
- Consumers must be **idempotent** — process the same event twice without side effects
- Use `event_id` for deduplication
- On failure: retry 3 times with exponential backoff, then send to DLQ
- Log every consumed event with `event_id` and `correlation_id`
- Consumer offset commits: after processing (at-least-once delivery)

## Schema Registry
- JSON Schema format
- Compatibility mode: BACKWARD
- Schemas stored in `infra/kafka/schemas/`
