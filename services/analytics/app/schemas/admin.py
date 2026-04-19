from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeadLetterMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic: str
    partition: int
    offset: int
    event_type: str | None = None
    error_message: str
    retry_count: int
    raw_message: dict[str, Any]
    replayed_at: datetime | None = None
    created_at: datetime
