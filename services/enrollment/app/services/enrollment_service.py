from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enrollment import Enrollment
from app.models.enrollment_audit import EnrollmentAudit
from app.repositories.enrollment_audit_repository import EnrollmentAuditRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.outbox_repository import OutboxRepository
from app.schemas.enrollment import EnrollmentCreate, EnrollmentResponse, EnrollmentStatusResponse
from app.services.course_client import CourseClient
from app.services.progress_client import ProgressClient
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.errors import EduCorpError, ForbiddenError, NotFoundError


class EnrollmentService:
    """Enrollment business logic and orchestration."""

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        *,
        course_client: CourseClient | None = None,
        progress_client: ProgressClient | None = None,
    ) -> None:
        self._session = session
        self._redis = redis
        self._enrollments = EnrollmentRepository(session)
        self._audits = EnrollmentAuditRepository(session)
        self._outbox = OutboxRepository(session)
        self._course_client = course_client or CourseClient()
        self._progress_client = progress_client or ProgressClient()

    async def create_enrollment(
        self,
        *,
        current_user: CurrentUser,
        payload: EnrollmentCreate,
        correlation_id: str,
    ) -> tuple[EnrollmentResponse, bool]:
        student_id = UUID(current_user["id"])
        if "student" not in current_user["roles"] and "admin" not in current_user["roles"]:
            raise ForbiddenError("Only students can enroll in courses")

        if payload.idempotency_key:
            cached = await self._get_cached_idempotent_enrollment(payload.idempotency_key)
            if cached is not None:
                return cached, True

        course_context = await self._course_client.get_enrollment_context(course_id=payload.course_id)
        self._validate_course_enrollable(course_context)

        existing = await self._enrollments.get_by_student_course(
            student_id=student_id,
            course_id=payload.course_id,
        )
        if existing is not None:
            if existing.status == "CANCELLED":
                raise EduCorpError(
                    code="ENROLLMENT_CANCELLED",
                    message="Enrollment was previously cancelled and cannot be recreated",
                    status_code=409,
                )
            response = self._to_response(existing)
            if payload.idempotency_key:
                await self._cache_idempotent_enrollment(payload.idempotency_key, response)
            return response, True

        prerequisite_ids = [UUID(prereq) for prereq in course_context.get("prerequisites", [])]
        await self._ensure_prerequisites(
            student_id=student_id,
            enrollment_id=None,
            prerequisite_ids=prerequisite_ids,
            correlation_id=correlation_id,
        )

        async with self._course_capacity_lock(course_id=payload.course_id, max_capacity=course_context.get("max_capacity")):
            await self._ensure_capacity(
                course_id=payload.course_id,
                max_capacity=course_context.get("max_capacity"),
                correlation_id=correlation_id,
                actor_id=student_id,
            )
            enrollment = Enrollment(
                student_id=student_id,
                course_id=payload.course_id,
                status="ENROLLED",
                idempotency_key=payload.idempotency_key,
                enrolled_at=datetime.now(timezone.utc),
            )
            await self._enrollments.create(enrollment)
            await self._write_audit(
                enrollment_id=enrollment.id,
                action="ENROLLED",
                actor_id=student_id,
                details={"course_id": str(payload.course_id)},
                correlation_id=correlation_id,
            )
            await self._outbox.write(
                aggregate_type="enrollment",
                aggregate_id=enrollment.id,
                event_type="EnrollmentCreated",
                data={
                    "enrollment_id": str(enrollment.id),
                    "student_id": str(student_id),
                    "course_id": str(payload.course_id),
                    "course_title": str(course_context["title"]),
                },
                metadata=self._event_metadata(correlation_id, student_id),
                correlation_id=self._parse_uuid(correlation_id),
            )
            await self._session.commit()

        await self._progress_client.initialize_progress(
            enrollment_id=enrollment.id,
            student_id=student_id,
            course_context=course_context,
            enrolled_at=enrollment.enrolled_at,
        )

        response = self._to_response(enrollment)
        if payload.idempotency_key:
            await self._cache_idempotent_enrollment(payload.idempotency_key, response)
        await self._invalidate_status_cache(student_id=student_id, course_id=payload.course_id)
        return response, False

    async def list_enrollments(
        self,
        *,
        current_user: CurrentUser,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[EnrollmentResponse], int]:
        student_id = UUID(current_user["id"])
        enrollments, total = await self._enrollments.list_for_student(
            student_id=student_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return [self._to_response(item) for item in enrollments], total

    async def get_enrollment(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
    ) -> EnrollmentResponse:
        enrollment = await self._require_owned_enrollment(
            current_user=current_user,
            enrollment_id=enrollment_id,
        )
        return self._to_response(enrollment)

    async def cancel_enrollment(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
        correlation_id: str,
    ) -> EnrollmentResponse:
        enrollment = await self._require_owned_enrollment(
            current_user=current_user,
            enrollment_id=enrollment_id,
        )
        if enrollment.status != "ENROLLED":
            raise EduCorpError(
                code="ENROLLMENT_CANNOT_CANCEL",
                message="Only active enrollments can be cancelled",
                status_code=409,
            )
        enrollment.status = "CANCELLED"
        enrollment.cancelled_at = datetime.now(timezone.utc)
        await self._enrollments.update(enrollment)
        await self._write_audit(
            enrollment_id=enrollment.id,
            action="CANCELLED",
            actor_id=UUID(current_user["id"]),
            details={"course_id": str(enrollment.course_id)},
            correlation_id=correlation_id,
        )
        await self._outbox.write(
            aggregate_type="enrollment",
            aggregate_id=enrollment.id,
            event_type="EnrollmentCancelled",
            data={
                "enrollment_id": str(enrollment.id),
                "student_id": str(enrollment.student_id),
                "course_id": str(enrollment.course_id),
            },
            metadata=self._event_metadata(correlation_id, UUID(current_user["id"])),
            correlation_id=self._parse_uuid(correlation_id),
        )
        await self._session.commit()
        await self._invalidate_status_cache(
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
        )
        return self._to_response(enrollment)

    async def get_enrollment_status(
        self,
        *,
        current_user: CurrentUser,
        course_id: UUID,
    ) -> EnrollmentStatusResponse:
        student_id = UUID(current_user["id"])
        cached = await self._redis.get(self._status_cache_key(student_id=student_id, course_id=course_id))
        if cached is not None:
            progress_percent = float(cached)
            enrollment = await self._enrollments.get_by_student_course(
                student_id=student_id,
                course_id=course_id,
            )
            if enrollment is None:
                return EnrollmentStatusResponse(is_enrolled=False)
            return EnrollmentStatusResponse(
                is_enrolled=enrollment.status != "CANCELLED",
                enrollment_id=enrollment.id,
                status=enrollment.status,
                progress_percent=progress_percent,
            )

        enrollment = await self._enrollments.get_by_student_course(
            student_id=student_id,
            course_id=course_id,
        )
        if enrollment is None or enrollment.status == "CANCELLED":
            return EnrollmentStatusResponse(is_enrolled=False)
        summary = await self._progress_client.get_progress_summary(enrollment_id=enrollment.id)
        progress_percent = float(summary["progress_percent"]) if summary is not None else 0.0
        await self._redis.set(
            self._status_cache_key(student_id=student_id, course_id=course_id),
            str(progress_percent),
            ex=settings.enrollment_status_cache_ttl_seconds,
        )
        return EnrollmentStatusResponse(
            is_enrolled=True,
            enrollment_id=enrollment.id,
            status=enrollment.status,
            progress_percent=progress_percent,
        )

    async def mark_completed(
        self,
        *,
        enrollment_id: UUID,
        completed_at: datetime,
        correlation_id: str,
    ) -> EnrollmentResponse:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        if enrollment.status != "COMPLETED":
            enrollment.status = "COMPLETED"
            enrollment.completed_at = completed_at
            await self._enrollments.update(enrollment)
            await self._write_audit(
                enrollment_id=enrollment.id,
                action="COMPLETED",
                actor_id=enrollment.student_id,
                details={"course_id": str(enrollment.course_id)},
                correlation_id=correlation_id,
            )
            await self._session.commit()
            await self._invalidate_status_cache(
                student_id=enrollment.student_id,
                course_id=enrollment.course_id,
            )
        return self._to_response(enrollment)

    async def _require_owned_enrollment(
        self,
        *,
        current_user: CurrentUser,
        enrollment_id: UUID,
    ) -> Enrollment:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        if "admin" in current_user["roles"]:
            return enrollment
        if enrollment.student_id != UUID(current_user["id"]):
            raise ForbiddenError("You do not have access to this enrollment")
        return enrollment

    async def _ensure_prerequisites(
        self,
        *,
        student_id: UUID,
        enrollment_id: UUID | None,
        prerequisite_ids: list[UUID],
        correlation_id: str,
    ) -> None:
        completed_ids = await self._enrollments.list_completed_course_ids(
            student_id=student_id,
            course_ids=prerequisite_ids,
        )
        missing = [course_id for course_id in prerequisite_ids if course_id not in completed_ids]
        if missing:
            raise EduCorpError(
                code="ENROLLMENT_PREREQUISITES_NOT_MET",
                message="Course prerequisites are not complete",
                status_code=409,
                details=[{"missing_course_id": str(course_id)} for course_id in missing],
            )
        if enrollment_id is not None:
            await self._write_audit(
                enrollment_id=enrollment_id,
                action="PREREQUISITE_CHECK",
                actor_id=student_id,
                details={"count": len(prerequisite_ids)},
                correlation_id=correlation_id,
            )

    async def _ensure_capacity(
        self,
        *,
        course_id: UUID,
        max_capacity: int | None,
        correlation_id: str,
        actor_id: UUID,
    ) -> None:
        if max_capacity is None:
            return
        count = await self._enrollments.count_active_for_course(course_id=course_id)
        if count >= max_capacity:
            raise EduCorpError(
                code="ENROLLMENT_CAPACITY_EXCEEDED",
                message="Course capacity has been reached",
                status_code=409,
            )
        _ = correlation_id
        _ = actor_id

    def _validate_course_enrollable(self, course_context: dict[str, Any]) -> None:
        if course_context.get("visibility") != "PUBLISHED" or not course_context.get("current_version_id"):
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not currently open for enrollment",
                status_code=409,
            )

    async def _cache_idempotent_enrollment(
        self,
        idempotency_key: str,
        response: EnrollmentResponse,
    ) -> None:
        await self._redis.set(
            self._idempotency_cache_key(idempotency_key),
            str(response.id),
            ex=settings.enrollment_idempotency_ttl_seconds,
        )

    async def _get_cached_idempotent_enrollment(
        self,
        idempotency_key: str,
    ) -> EnrollmentResponse | None:
        cached_id = await self._redis.get(self._idempotency_cache_key(idempotency_key))
        if cached_id is None:
            return None
        enrollment = await self._enrollments.get_by_id(UUID(cached_id))
        if enrollment is None:
            return None
        return self._to_response(enrollment)

    async def _invalidate_status_cache(self, *, student_id: UUID, course_id: UUID) -> None:
        await self._redis.delete(self._status_cache_key(student_id=student_id, course_id=course_id))

    async def _write_audit(
        self,
        *,
        enrollment_id: UUID,
        action: str,
        actor_id: UUID,
        details: dict[str, Any],
        correlation_id: str,
    ) -> None:
        await self._audits.create(
            EnrollmentAudit(
                enrollment_id=enrollment_id,
                action=action,
                actor_id=actor_id,
                details=details,
                correlation_id=self._parse_uuid(correlation_id),
            )
        )

    @asynccontextmanager
    async def _course_capacity_lock(self, *, course_id: UUID, max_capacity: int | None):
        if max_capacity is None:
            yield
            return
        key = f"lock:enrollment:{course_id}"
        token = str(uuid4())
        acquired = await self._redis.set(
            key,
            token,
            ex=settings.enrollment_lock_ttl_seconds,
            nx=True,
        )
        if not acquired:
            raise EduCorpError(
                code="ENROLLMENT_CAPACITY_LOCKED",
                message="Enrollment is busy for this course; retry the request",
                status_code=409,
            )
        try:
            yield
        finally:
            existing = await self._redis.get(key)
            if existing == token:
                await self._redis.delete(key)

    @staticmethod
    def _to_response(enrollment: Enrollment) -> EnrollmentResponse:
        return EnrollmentResponse(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            status=enrollment.status,
            enrolled_at=enrollment.enrolled_at,
            cancelled_at=enrollment.cancelled_at,
            completed_at=enrollment.completed_at,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
        )

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError:
            return uuid4()

    @staticmethod
    def _event_metadata(correlation_id: str, actor_id: UUID) -> dict[str, Any]:
        return {
            "correlation_id": correlation_id,
            "actor_id": str(actor_id),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
        }

    @staticmethod
    def _idempotency_cache_key(idempotency_key: str) -> str:
        return f"idempotency:{idempotency_key}"

    @staticmethod
    def _status_cache_key(*, student_id: UUID, course_id: UUID) -> str:
        return f"cache:enrolled:{student_id}:{course_id}"