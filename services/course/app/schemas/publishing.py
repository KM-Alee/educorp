from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class PublishVersionResponse(BaseModel):
    version_id: UUID
    version_number: int
    status: str
    workflow_id: str | None
    message: str
