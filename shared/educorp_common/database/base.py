from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin adding created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SoftDeleteMixin:
    """Mixin adding soft-delete support via deleted_at column."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class UUIDPrimaryKeyMixin:
    """Mixin adding UUID primary key."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
