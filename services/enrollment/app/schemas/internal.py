from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnrollmentCompletionRequest(BaseModel):
    """Internal callback payload used by progress service on course completion."""

    completed_at: datetime


class EnrollmentAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enrollment_id: UUID
    action: str
    actor_id: UUID
    details: dict[str, Any]
    correlation_id: UUID | None = None
    created_at: datetime
