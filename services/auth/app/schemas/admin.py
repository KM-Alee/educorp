from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUpdateRolesRequest(BaseModel):
    add_roles: list[str] = Field(default_factory=list)
    remove_roles: list[str] = Field(default_factory=list)


class AdminUpdateStatusRequest(BaseModel):
    is_active: bool


class AdminReviewInstructorApplicationRequest(BaseModel):
    status: str


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime
