from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.enrollment_audit import EnrollmentAudit
from app.repositories.course_repository import CourseRepository
from app.repositories.enrollment_audit_repository import EnrollmentAuditRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.progress_repository import ProgressRepository
from app.utils.redis_lock import RedisLock
from educorp_common.errors import EduCorpError, NotFoundError


@dataclass(slots=True)
class EnrollmentResult:
    enrollment: Enrollment
    idempotent_hit: bool


class EnrollmentService:
    """Enrollment workflows."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis
        self._enrollments = EnrollmentRepository(session)
        self._audits = EnrollmentAuditRepository(session)
        self._courses = CourseRepository(session)
        self._progress = ProgressRepository(session)
        self._outbox = OutboxRepository(session)

    async def enroll(
        self,
        *,
        student_id: UUID,
        course_id: UUID,
        idempotency_key: str | None,
        correlation_id: str,
    ) -> EnrollmentResult:
        if idempotency_key:
            existing = await self._enrollments.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return EnrollmentResult(existing, True)

        existing = await self._enrollments.get_by_student_course(student_id, course_id)
        if existing is not None:
            return EnrollmentResult(existing, True)

        course = await self._courses.get_course_meta(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if not course.is_ready:
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not ready for enrollment",
                status_code=409,
            )

        missing_prereqs = await self._missing_prerequisites(
            student_id=student_id,
            prerequisites=course.prerequisites,
        )
        if missing_prereqs:
            raise EduCorpError(
                code="ENROLLMENT_PREREQUISITES_NOT_MET",
                message="Prerequisites are not completed",
                status_code=409,
                details=[{"missing_prerequisites": [str(cid) for cid in missing_prereqs]}],
            )

        lock = RedisLock(self._redis, f"lock:enrollment:{course_id}", ttl_seconds=30)
        acquired = await lock.acquire(timeout_seconds=5.0)
        if not acquired:
            raise EduCorpError(
                code="ENROLLMENT_IN_PROGRESS",
                message="Enrollment is already in progress",
                status_code=409,
            )

        try:
            existing = await self._enrollments.get_by_student_course(student_id, course_id)
            if existing is not None:
                return EnrollmentResult(existing, True)

            if course.max_capacity is not None:
                current_count = await self._enrollments.count_active_by_course(course_id)
                if current_count >= course.max_capacity:
                    raise EduCorpError(
                        code="ENROLLMENT_CAPACITY_EXCEEDED",
                        message="Course has reached maximum enrollment capacity",
                        status_code=409,
                        details=[
                            {
                                "course_id": str(course_id),
                                "current_capacity": current_count,
                                "max_capacity": course.max_capacity,
                            }
                        ],
                    )

            enrollment = Enrollment(
                student_id=student_id,
                course_id=course_id,
                status="ENROLLED",
                idempotency_key=idempotency_key,
                enrolled_at=datetime.now(timezone.utc),
            )
            try:
                await self._enrollments.create(enrollment)
            except IntegrityError:
                existing = await self._enrollments.get_by_student_course(student_id, course_id)
                if existing is not None:
                    return EnrollmentResult(existing, True)
                raise

            await self._initialize_progress(enrollment, course_id)
            await self._audit_action(
                enrollment_id=enrollment.id,
                actor_id=student_id,
                action="PREREQUISITE_CHECK",
                details={"passed": True, "checked": [str(cid) for cid in course.prerequisites]},
                correlation_id=correlation_id,
            )
            await self._audit_action(
                enrollment_id=enrollment.id,
                actor_id=student_id,
                action="CAPACITY_CHECK",
                details={"passed": True, "max_capacity": course.max_capacity},
                correlation_id=correlation_id,
            )
            await self._audit_action(
                enrollment_id=enrollment.id,
                actor_id=student_id,
                action="ENROLLED",
                details={"course_id": str(course_id)},
                correlation_id=correlation_id,
            )
            await self._outbox.write(
                aggregate_type="enrollment",
                aggregate_id=enrollment.id,
                event_type="EnrollmentCreated",
                data={
                    "enrollment_id": str(enrollment.id),
                    "student_id": str(student_id),
                    "course_id": str(course_id),
                    "course_title": course.title,
                },
                metadata=self._event_metadata(correlation_id, student_id),
                correlation_id=self._parse_uuid(correlation_id),
            )

            return EnrollmentResult(enrollment, False)
        finally:
            await lock.release()

    async def list_enrollments(
        self,
        *,
        student_id: UUID,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Enrollment], int]:
        return await self._enrollments.list_by_student(
            student_id=student_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def get_enrollment(self, enrollment_id: UUID) -> Enrollment:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        return enrollment

    async def cancel_enrollment(
        self,
        *,
        enrollment: Enrollment,
        actor_id: UUID,
        correlation_id: str,
    ) -> Enrollment:
        if enrollment.status == "CANCELLED":
            return enrollment
        enrollment.status = "CANCELLED"
        enrollment.cancelled_at = datetime.now(timezone.utc)
        await self._enrollments.update(enrollment)
        await self._audit_action(
            enrollment_id=enrollment.id,
            actor_id=actor_id,
            action="CANCELLED",
            details={"course_id": str(enrollment.course_id)},
            correlation_id=correlation_id,
        )
        return enrollment

    async def get_enrollment_status(
        self, *, student_id: UUID, course_id: UUID
    ) -> tuple[Enrollment | None, float | None]:
        enrollment = await self._enrollments.get_by_student_course(student_id, course_id)
        if enrollment is None:
            return None, None
        progress_percent = await self._progress.get_progress_percent(enrollment.id)
        return enrollment, progress_percent

    async def _initialize_progress(self, enrollment: Enrollment, course_id: UUID) -> None:
        module_ids = await self._courses.list_required_module_ids(course_id)
        await self._progress.initialize_progress(
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=course_id,
            module_ids=module_ids,
        )

    async def _missing_prerequisites(
        self, *, student_id: UUID, prerequisites: list[UUID]
    ) -> list[UUID]:
        if not prerequisites:
            return []
        completed = await self._enrollments.list_completed_courses(student_id)
        completed_set = set(completed)
        return [course_id for course_id in prerequisites if course_id not in completed_set]

    async def _audit_action(
        self,
        *,
        enrollment_id: UUID,
        actor_id: UUID,
        action: str,
        details: dict,
        correlation_id: str,
    ) -> EnrollmentAudit:
        entry = EnrollmentAudit(
            enrollment_id=enrollment_id,
            action=action,
            actor_id=actor_id,
            details=details,
            correlation_id=self._parse_uuid(correlation_id),
        )
        return await self._audits.create(entry)

    def _event_metadata(self, correlation_id: str, actor_id: UUID) -> dict[str, str]:
        return {
            "correlation_id": correlation_id,
            "source_service": "enrollment",
            "actor_id": str(actor_id),
        }

    def _parse_uuid(self, value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError:
            return uuid4()
