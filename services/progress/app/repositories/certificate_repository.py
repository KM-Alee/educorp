from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate


class CertificateRepository:
    """Data access for completion certificates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, certificate: Certificate) -> Certificate:
        self._session.add(certificate)
        await self._session.flush()
        return certificate

    async def get_by_enrollment_id(self, *, enrollment_id) -> Certificate | None:
        result = await self._session.execute(
            select(Certificate).where(Certificate.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, *, certificate_id) -> Certificate | None:
        result = await self._session.execute(
            select(Certificate).where(Certificate.id == certificate_id)
        )
        return result.scalar_one_or_none()

    async def list_for_student(self, *, student_id) -> list[Certificate]:
        result = await self._session.execute(
            select(Certificate)
            .where(Certificate.student_id == student_id)
            .order_by(Certificate.issued_at.desc())
        )
        return list(result.scalars().all())

    async def count_for_student(self, *, student_id) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Certificate).where(Certificate.student_id == student_id)
        )
        return int(result.scalar_one())

    async def count_total(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(Certificate))
        return int(result.scalar_one())