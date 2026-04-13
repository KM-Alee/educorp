from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Many-to-many association between users and roles."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("idx_user_roles_user", "user_id"),
        {"schema": "auth"},
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"))
    role_id: Mapped[UUID] = mapped_column(ForeignKey("auth.roles.id", ondelete="CASCADE"))
    granted_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth.users.id"))
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())
