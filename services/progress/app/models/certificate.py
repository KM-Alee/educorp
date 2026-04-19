from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from educorp_common.database.base import Base, UUIDPrimaryKeyMixin


class Certificate(Base, UUIDPrimaryKeyMixin):
    """Course completion certificate."""

    __tablename__ = "certificates"
    __table_args__ = (
        Index("idx_certificates_student", "student_id"),
        Index("idx_certificates_number", "certificate_number"),
        {"schema": "progress"},
    )

    enrollment_id: Mapped[UUID] = mapped_column(unique=True)
    student_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    course_title: Mapped[str] = mapped_column(String(300))
    student_name: Mapped[str] = mapped_column(String(200))
    certificate_number: Mapped[str] = mapped_column(String(50), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cert_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
