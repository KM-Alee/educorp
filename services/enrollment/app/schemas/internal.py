from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EnrollmentCompletionRequest(BaseModel):
    """Internal callback payload used by progress service on course completion."""

    completed_at: datetime