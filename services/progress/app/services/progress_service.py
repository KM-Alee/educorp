from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate
from app.models.module_progress import ModuleProgress
from app.models.student_progress import StudentProgress
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.module_progress_repository import ModuleProgressRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.student_progress_repository import StudentProgressRepository
from app.schemas.internal import ProgressInitRequest, ProgressInitResponse, ProgressSummaryResponse
from app.schemas.progress import (
    CertificateDetailResponse,
    CertificateSummary,
    DashboardCourseProgress,
    DashboardResponse,
    ModuleCompletionResponse,
    ProgressCertificateSummary,
    ProgressDetailModule,
    ProgressDetailResponse,
)
from app.services.enrollment_client import EnrollmentClient
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.errors import ForbiddenError, NotFoundError


class ProgressService:
    """Progress initialization, tracking, and certificate issuance."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        enrollment_client: EnrollmentClient | None = None,
    ) -> None:
        self._session = session
        self._progress = StudentProgressRepository(session)
        self._modules = ModuleProgressRepository(session)
        self._certificates = CertificateRepository(session)
        self._outbox = OutboxRepository(session)
        self._enrollment_client = enrollment_client or EnrollmentClient()

    async def initialize_progress(self, *, payload: ProgressInitRequest, correlation_id: str) -> ProgressInitResponse:
        existing = await self._progress.get_by_enrollment_id(enrollment_id=payload.enrollment_id)
        if existing is not None:
            return ProgressInitResponse(
                enrollment_id=payload.enrollment_id,
                initialized=False,
                status=existing.status,
            )

        progress = StudentProgress(
            enrollment_id=payload.enrollment_id,
            student_id=payload.student_id,
            course_id=payload.course_id,
            course_title=payload.course_title,
            progress_percent=Decimal("0.00"),
            status="NOT_STARTED",
            started_at=payload.enrolled_at,
            last_activity_at=payload.enrolled_at,
        )
        await self._progress.create(progress)
        module_rows = [
            ModuleProgress(
                student_progress_id=progress.id,
                module_id=module.id,
                module_title=module.title,
                sort_order=module.sort_order,
                is_required=module.is_required,
                is_completed=False,
                progress_percent=Decimal("0.00"),
            )
            for module in payload.modules
        ]
        await self._modules.create_many(module_rows)
        await self._session.commit()
        return ProgressInitResponse(
            enrollment_id=payload.enrollment_id,
            initialized=True,
            status=progress.status,
        )

    async def get_progress_detail(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
    ) -> ProgressDetailResponse:
        progress = await self._require_owned_progress(current_user=current_user, enrollment_id=enrollment_id)
        modules = await self._modules.list_for_progress(student_progress_id=progress.id)
        return self._to_detail(progress, modules)

    async def get_progress_summary(self, *, enrollment_id: UUID) -> ProgressSummaryResponse:
        progress = await self._progress.get_by_enrollment_id(enrollment_id=enrollment_id)
        if progress is None:
            raise NotFoundError("Progress not found")
        return ProgressSummaryResponse(
            enrollment_id=enrollment_id,
            progress_percent=float(progress.progress_percent),
            status=progress.status,
        )

    async def complete_module(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
        module_id: UUID,
        correlation_id: str,
    ) -> ModuleCompletionResponse:
        progress = await self._require_owned_progress(current_user=current_user, enrollment_id=enrollment_id)
        module = await self._modules.get_by_progress_and_module(
            student_progress_id=progress.id,
            module_id=module_id,
        )
        if module is None:
            raise NotFoundError("Module progress not found")

        now = datetime.now(timezone.utc)
        if not module.is_completed:
            module.is_completed = True
            module.progress_percent = Decimal("100.00")
            module.started_at = module.started_at or now
            module.completed_at = now
            await self._modules.update(module)

        modules = await self._modules.list_for_progress(student_progress_id=progress.id)
        required_modules = [item for item in modules if item.is_required]
        considered = required_modules or modules
        completed_required = len([item for item in considered if item.is_completed])
        total_required = len(considered)
        percent = Decimal("100.00") if total_required == 0 else (Decimal(completed_required) / Decimal(total_required)) * Decimal("100")
        progress.progress_percent = percent.quantize(Decimal("0.01"))
        progress.last_activity_at = now
        if completed_required == 0:
            progress.status = "NOT_STARTED"
        elif completed_required < total_required:
            progress.status = "IN_PROGRESS"
            progress.started_at = progress.started_at or now
        else:
            progress.status = "COMPLETED"
            progress.completed_at = progress.completed_at or now
        await self._progress.update(progress)

        certificate_summary: ProgressCertificateSummary | None = None
        course_completed = progress.status == "COMPLETED"
        if course_completed:
            certificate = await self._certificates.get_by_enrollment_id(enrollment_id=enrollment_id)
            if certificate is None:
                certificate = await self._create_certificate(progress=progress, current_user=current_user)
                await self._outbox.write(
                    aggregate_type="progress",
                    aggregate_id=progress.id,
                    event_type="CourseCompleted",
                    data={
                        "enrollment_id": str(progress.enrollment_id),
                        "student_id": str(progress.student_id),
                        "course_id": str(progress.course_id),
                        "certificate_id": str(certificate.id),
                        "certificate_number": certificate.certificate_number,
                        "completed_at": progress.completed_at.isoformat() if progress.completed_at else now.isoformat(),
                    },
                    metadata=self._event_metadata(correlation_id, progress.student_id),
                    correlation_id=self._parse_uuid(correlation_id),
                )
                await self._session.commit()
                await self._enrollment_client.mark_completed(
                    enrollment_id=progress.enrollment_id,
                    completed_at=progress.completed_at or now,
                )
            else:
                await self._session.commit()
            certificate_summary = ProgressCertificateSummary(
                id=certificate.id,
                certificate_number=certificate.certificate_number,
                issued_at=certificate.issued_at,
            )
        else:
            await self._session.commit()

        return ModuleCompletionResponse(
            module_id=module_id,
            is_completed=True,
            completed_at=module.completed_at,
            overall_progress_percent=float(progress.progress_percent),
            course_completed=course_completed,
            certificate=certificate_summary,
        )

    async def get_dashboard(self, *, current_user: CurrentUser) -> DashboardResponse:
        student_id = UUID(current_user["id"])
        progress_rows = await self._progress.list_for_student(student_id=student_id)
        certificates = await self._certificates.count_for_student(student_id=student_id)
        completed_courses = len([item for item in progress_rows if item.status == "COMPLETED"])
        active_courses = len([item for item in progress_rows if item.status != "COMPLETED"])
        return DashboardResponse(
            active_courses=active_courses,
            completed_courses=completed_courses,
            total_certificates=certificates,
            courses=[
                DashboardCourseProgress(
                    course_id=item.course_id,
                    course_title=item.course_title,
                    progress_percent=float(item.progress_percent),
                    status=item.status,
                    last_activity_at=item.last_activity_at,
                )
                for item in progress_rows
            ],
        )

    async def list_certificates(self, *, current_user: CurrentUser) -> list[CertificateSummary]:
        certificates = await self._certificates.list_for_student(student_id=UUID(current_user["id"]))
        return [
            CertificateSummary(
                id=certificate.id,
                enrollment_id=certificate.enrollment_id,
                course_id=certificate.course_id,
                course_title=certificate.course_title,
                certificate_number=certificate.certificate_number,
                issued_at=certificate.issued_at,
            )
            for certificate in certificates
        ]

    async def get_certificate_detail(self, *, certificate_id: UUID) -> CertificateDetailResponse:
        certificate = await self._certificates.get_by_id(certificate_id=certificate_id)
        if certificate is None:
            raise NotFoundError("Certificate not found")
        return CertificateDetailResponse(
            id=certificate.id,
            enrollment_id=certificate.enrollment_id,
            student_id=certificate.student_id,
            course_id=certificate.course_id,
            course_title=certificate.course_title,
            student_name=certificate.student_name,
            certificate_number=certificate.certificate_number,
            issued_at=certificate.issued_at,
            metadata=certificate.certificate_metadata,
        )

    async def _require_owned_progress(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
    ) -> StudentProgress:
        progress = await self._progress.get_by_enrollment_id(enrollment_id=enrollment_id)
        if progress is None:
            raise NotFoundError("Progress not found")
        if "admin" in current_user["roles"]:
            return progress
        if progress.student_id != UUID(current_user["id"]):
            raise ForbiddenError("You do not have access to this progress")
        return progress

    async def _create_certificate(
        self,
        *,
        progress: StudentProgress,
        current_user: CurrentUser,
    ) -> Certificate:
        sequence = await self._certificates.count_total() + 1
        certificate = Certificate(
            enrollment_id=progress.enrollment_id,
            student_id=progress.student_id,
            course_id=progress.course_id,
            course_title=progress.course_title,
            student_name=current_user.get("email", f"Student {progress.student_id}"),
            certificate_number=f"SC-{datetime.now(timezone.utc).year}-{sequence:05d}",
            certificate_metadata={"issued_for_status": progress.status},
        )
        return await self._certificates.create(certificate)

    @staticmethod
    def _to_detail(progress: StudentProgress, modules: list[ModuleProgress]) -> ProgressDetailResponse:
        return ProgressDetailResponse(
            enrollment_id=progress.enrollment_id,
            course_id=progress.course_id,
            course_title=progress.course_title,
            progress_percent=float(progress.progress_percent),
            status=progress.status,
            started_at=progress.started_at,
            last_activity_at=progress.last_activity_at,
            completed_at=progress.completed_at,
            modules=[
                ProgressDetailModule(
                    module_id=module.module_id,
                    module_title=module.module_title,
                    is_completed=module.is_completed,
                    progress_percent=float(module.progress_percent),
                    completed_at=module.completed_at,
                )
                for module in modules
            ],
        )

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError:
            return uuid4()

    @staticmethod
    def _event_metadata(correlation_id: str, actor_id: UUID) -> dict[str, str | int]:
        return {
            "correlation_id": correlation_id,
            "actor_id": str(actor_id),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
        }