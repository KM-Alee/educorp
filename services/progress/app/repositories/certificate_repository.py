from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate


class CertificateRepository:
    """Certificate data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, certificate: Certificate) -> Certificate:
        self._session.add(certificate)
        await self._session.flush()
        return certificate

    async def get_by_enrollment(self, enrollment_id: UUID) -> Certificate | None:
        result = await self._session.execute(
            select(Certificate).where(Certificate.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, certificate_id: UUID) -> Certificate | None:
        result = await self._session.execute(
            select(Certificate).where(Certificate.id == certificate_id)
        )
        return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[Certificate]:
        result = await self._session.execute(
            select(Certificate)
            .where(Certificate.student_id == student_id)
            .order_by(Certificate.issued_at.desc())
        )
        return list(result.scalars().all())

    async def exists_number(self, certificate_number: str) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(Certificate).where(
                Certificate.certificate_number == certificate_number
            )
        )
        return int(result.scalar_one()) > 0
