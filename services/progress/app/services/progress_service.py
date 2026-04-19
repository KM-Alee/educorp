from __future__ import annotations

from datetime import datetime, timezone
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.module_progress_repository import ModuleProgressRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.student_progress_repository import StudentProgressRepository
from app.repositories.user_repository import UserRepository
from app.schemas.progress import (
    CertificateDetailOut,
    CertificateOut,
    DashboardCourseOut,
    EnrollmentProgressOut,
    ModuleCompletionCertificate,
    ModuleCompletionOut,
    ModuleProgressOut,
    ProgressDashboardOut,
)
from educorp_common.errors import EduCorpError, ForbiddenError, NotFoundError


class ProgressService:
    """Progress tracking workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._enrollments = EnrollmentRepository(session)
        self._student_progress = StudentProgressRepository(session)
        self._module_progress = ModuleProgressRepository(session)
        self._certificates = CertificateRepository(session)
        self._courses = CourseRepository(session)
        self._users = UserRepository(session)
        self._outbox = OutboxRepository(session)

    async def get_enrollment_progress(
        self, *, enrollment_id: UUID, user_id: UUID, roles: list[str]
    ) -> EnrollmentProgressOut:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        is_admin = "admin" in roles
        if not is_admin and enrollment.student_id != user_id:
            raise ForbiddenError("Access forbidden")

        progress = await self._student_progress.get_by_enrollment(enrollment_id)
        if progress is None:
            raise NotFoundError("Progress not found")

        module_rows = await self._module_progress.list_with_titles(progress.id)
        modules = [
            ModuleProgressOut(
                module_id=UUID(str(row["module_id"])),
                module_title=str(row["title"]),
                is_completed=bool(row["is_completed"]),
                progress_percent=float(row["progress_percent"] or 0.0),
                completed_at=row.get("completed_at"),
            )
            for row in module_rows
        ]

        return EnrollmentProgressOut(
            enrollment_id=enrollment.enrollment_id,
            course_id=enrollment.course_id,
            progress_percent=float(progress.progress_percent or 0.0),
            status=progress.status,
            started_at=progress.started_at,
            last_activity_at=progress.last_activity_at,
            modules=modules,
        )

    async def complete_module(
        self,
        *,
        enrollment_id: UUID,
        module_id: UUID,
        student_id: UUID,
        correlation_id: str,
    ) -> ModuleCompletionOut:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        if enrollment.student_id != student_id:
            raise ForbiddenError("Access forbidden")
        if enrollment.status == "CANCELLED":
            raise EduCorpError(
                code="ENROLLMENT_CANCELLED",
                message="Enrollment has been cancelled",
                status_code=409,
            )

        progress = await self._student_progress.get_by_enrollment(enrollment_id)
        if progress is None:
            raise NotFoundError("Progress not found")

        module_progress = await self._module_progress.get_by_student_progress_and_module(
            progress.id, module_id
        )
        if module_progress is None:
            raise NotFoundError("Module progress not found")

        if module_progress.is_completed:
            overall_percent = float(progress.progress_percent or 0.0)
            certificate = await self._certificates.get_by_enrollment(enrollment_id)
            return ModuleCompletionOut(
                module_id=module_id,
                is_completed=True,
                completed_at=module_progress.completed_at,
                overall_progress_percent=overall_percent,
                course_completed=progress.status == "COMPLETED",
                certificate=_certificate_payload(certificate),
            )

        now = datetime.now(timezone.utc)
        module_progress.is_completed = True
        module_progress.progress_percent = 100.0
        module_progress.completed_at = now
        if module_progress.started_at is None:
            module_progress.started_at = now
        await self._module_progress.update(module_progress)

        total_modules = await self._module_progress.count_total(progress.id)
        completed_modules = await self._module_progress.count_completed(progress.id)
        overall_percent = _calculate_percent(completed_modules, total_modules)

        progress.progress_percent = overall_percent
        if progress.started_at is None:
            progress.started_at = now
        progress.last_activity_at = now

        course_completed = total_modules > 0 and completed_modules == total_modules
        certificate = None
        if course_completed:
            progress.status = "COMPLETED"
            progress.completed_at = now
            progress.progress_percent = 100.0
            await self._enrollments.mark_completed(enrollment_id)
            certificate = await self._issue_certificate(
                enrollment_id=enrollment_id,
                student_id=student_id,
                course_id=enrollment.course_id,
                completed_at=now,
                correlation_id=correlation_id,
            )
        elif progress.status == "NOT_STARTED":
            progress.status = "IN_PROGRESS"

        await self._student_progress.update(progress)

        return ModuleCompletionOut(
            module_id=module_id,
            is_completed=True,
            completed_at=module_progress.completed_at,
            overall_progress_percent=float(progress.progress_percent or 0.0),
            course_completed=course_completed,
            certificate=_certificate_payload(certificate),
        )

    async def get_dashboard(self, student_id: UUID) -> ProgressDashboardOut:
        query = text(
            "SELECT sp.course_id, sp.progress_percent, sp.status, sp.last_activity_at, c.title "
            "FROM progress.student_progress sp "
            "JOIN course.courses c ON c.id = sp.course_id "
            "WHERE sp.student_id = :student_id AND c.deleted_at IS NULL "
            "ORDER BY sp.last_activity_at DESC NULLS LAST"
        )
        result = await self._session.execute(query, {"student_id": str(student_id)})
        rows = result.mappings().all()
        courses = [
            DashboardCourseOut(
                course_id=UUID(str(row["course_id"])),
                course_title=str(row["title"]),
                progress_percent=float(row["progress_percent"] or 0.0),
                status=str(row["status"]),
                last_activity_at=row.get("last_activity_at"),
            )
            for row in rows
        ]

        completed_courses = len([c for c in courses if c.status == "COMPLETED"])
        active_courses = len(courses) - completed_courses
        total_certificates = len(await self._certificates.list_by_student(student_id))

        return ProgressDashboardOut(
            active_courses=active_courses,
            completed_courses=completed_courses,
            total_certificates=total_certificates,
            courses=courses,
        )

    async def list_certificates(self, student_id: UUID) -> list[CertificateOut]:
        certificates = await self._certificates.list_by_student(student_id)
        return [
            CertificateOut(
                id=cert.id,
                course_id=cert.course_id,
                course_title=cert.course_title,
                certificate_number=cert.certificate_number,
                issued_at=cert.issued_at,
            )
            for cert in certificates
        ]

    async def get_certificate(self, certificate_id: UUID) -> CertificateDetailOut:
        certificate = await self._certificates.get_by_id(certificate_id)
        if certificate is None:
            raise NotFoundError("Certificate not found")
        return CertificateDetailOut(
            id=certificate.id,
            enrollment_id=certificate.enrollment_id,
            student_id=certificate.student_id,
            course_id=certificate.course_id,
            course_title=certificate.course_title,
            student_name=certificate.student_name,
            certificate_number=certificate.certificate_number,
            issued_at=certificate.issued_at,
            metadata=certificate.metadata or {},
        )

    async def _issue_certificate(
        self,
        *,
        enrollment_id: UUID,
        student_id: UUID,
        course_id: UUID,
        completed_at: datetime,
        correlation_id: str,
    ) -> Certificate:
        existing = await self._certificates.get_by_enrollment(enrollment_id)
        if existing is not None:
            return existing

        course_title = await self._courses.get_course_title(course_id)
        if course_title is None:
            raise NotFoundError("Course not found")
        student_name = await self._users.get_full_name(student_id)
        if student_name is None:
            raise NotFoundError("Student not found")

        certificate_number = await self._generate_certificate_number()
        certificate = Certificate(
            enrollment_id=enrollment_id,
            student_id=student_id,
            course_id=course_id,
            course_title=course_title,
            student_name=student_name,
            certificate_number=certificate_number,
            issued_at=completed_at,
            metadata={},
        )
        await self._certificates.create(certificate)

        await self._outbox.write(
            aggregate_type="enrollment",
            aggregate_id=enrollment_id,
            event_type="CourseCompleted",
            data={
                "enrollment_id": str(enrollment_id),
                "student_id": str(student_id),
                "course_id": str(course_id),
                "certificate_id": str(certificate.id),
                "certificate_number": certificate.certificate_number,
                "completed_at": completed_at.isoformat(),
            },
            metadata=self._event_metadata(correlation_id, student_id),
            correlation_id=self._parse_uuid(correlation_id),
        )
        return certificate

    async def _generate_certificate_number(self) -> str:
        year = datetime.now(timezone.utc).year
        for _ in range(10):
            suffix = secrets.randbelow(100000)
            certificate_number = f"SC-{year}-{suffix:05d}"
            if not await self._certificates.exists_number(certificate_number):
                return certificate_number
        raise EduCorpError(
            code="CERTIFICATE_NUMBER_GENERATION_FAILED",
            message="Unable to generate certificate number",
            status_code=500,
        )

    def _event_metadata(self, correlation_id: str, actor_id: UUID) -> dict[str, str]:
        return {
            "correlation_id": correlation_id,
            "source_service": "progress",
            "actor_id": str(actor_id),
        }

    def _parse_uuid(self, value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError:
            return uuid4()


def _calculate_percent(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((completed / total) * 100.0, 2)


def _certificate_payload(
    certificate: Certificate | None,
) -> ModuleCompletionCertificate | None:
    if certificate is None:
        return None
    return ModuleCompletionCertificate(
        id=certificate.id,
        certificate_number=certificate.certificate_number,
        issued_at=certificate.issued_at,
    )
