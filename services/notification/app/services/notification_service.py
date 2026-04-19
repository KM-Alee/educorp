from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.repositories.notification_preference_repository import NotificationPreferenceRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.auth_client import AuthClient
from app.tasks import send_email_task
from educorp_common.errors import ForbiddenError, NotFoundError
from educorp_common.events import DomainEvent, DomainEventIngestResult

logger = structlog.get_logger()


class NotificationService:
    """Notification read APIs and Phase 6 event handling."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = NotificationRepository(session)
        self._preferences = NotificationPreferenceRepository(session)
        self._auth_client = AuthClient()

    async def list_notifications(
        self,
        *,
        user_id: UUID,
        is_read: bool | None,
        limit: int,
    ) -> list[Notification]:
        return await self._notifications.list_for_user(
            user_id=user_id, is_read=is_read, limit=limit
        )

    async def mark_read(self, *, notification_id: UUID, user_id: UUID) -> Notification:
        notification = await self._notifications.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.user_id != user_id:
            raise ForbiddenError("Access forbidden")
        return await self._notifications.mark_read(notification)

    async def mark_all_read(self, *, user_id: UUID) -> int:
        return await self._notifications.mark_all_read(user_id=user_id)

    async def get_preferences(self, *, user_id: UUID) -> NotificationPreference:
        return await self._preferences.get_or_create(user_id)

    async def update_preferences(
        self,
        *,
        user_id: UUID,
        updates: dict[str, bool | None],
    ) -> NotificationPreference:
        preference = await self._preferences.get_or_create(user_id)
        for field, value in updates.items():
            if value is not None:
                setattr(preference, field, value)
        return await self._preferences.update(preference)

    async def ingest_events(self, events: list[DomainEvent]) -> DomainEventIngestResult:
        processed = 0
        skipped = 0
        for event in events:
            created = await self._handle_event(event)
            if created:
                processed += 1
            else:
                skipped += 1
        return DomainEventIngestResult(processed_count=processed, skipped_count=skipped)

    async def _handle_event(self, event: DomainEvent) -> bool:
        template = _template_for_event(event.event_type)
        if template is None:
            return False

        recipient_id = _resolve_recipient_id(event)
        if recipient_id is None:
            logger.warning("Notification event missing recipient", event_type=event.event_type)
            return False

        user_id = UUID(recipient_id)
        prefs = await self._preferences.get_or_create(user_id)
        context = await self._context_for_event(user_id=user_id, event=event)

        if getattr(prefs, template["in_app_pref"]):
            existing = await self._notifications.get_by_source_event(
                user_id=user_id,
                channel="in_app",
                source_event_id=event.event_id,
            )
            if existing is None:
                await self._notifications.create(
                    Notification(
                        user_id=user_id,
                        type=template["notification_type"],
                        channel="in_app",
                        title=str(template["title"](context)),
                        message=str(template["message"](context)),
                        source_event_id=event.event_id,
                        notification_metadata=_notification_metadata(event, context),
                    )
                )

        if getattr(prefs, template["email_pref"]):
            email = _opt_str(context.get("recipient_email"))
            if email:
                try:
                    send_email_task.delay(
                        to=email,
                        subject=str(template["title"](context)),
                        body=str(template["email_body"](context)),
                    )
                except Exception:
                    logger.warning("Failed to enqueue notification email", to=email)

        return True

    async def _context_for_event(self, *, user_id: UUID, event: DomainEvent) -> dict[str, Any]:
        context = dict(event.payload)
        try:
            summary = await self._auth_client.get_user_summary(user_id=user_id)
        except Exception:
            logger.warning("Failed to enrich notification recipient", user_id=str(user_id))
            summary = None
        if summary:
            context.setdefault("recipient_email", summary.get("email"))
            context.setdefault("recipient_name", summary.get("full_name"))
        context.setdefault("recipient_name", "learner")
        context.setdefault("recipient_email", None)
        context.setdefault("course_title", "your course")
        context.setdefault("certificate_number", "")
        context.setdefault("version_number", None)
        return context


def _template_for_event(event_type: str) -> dict[str, Any] | None:
    templates: dict[str, dict[str, Any]] = {
        "EnrollmentCreated": {
            "notification_type": "enrollment_confirmed",
            "in_app_pref": "enrollment_confirmed_in_app",
            "email_pref": "enrollment_confirmed_email",
            "title": lambda ctx: f"You are enrolled in {ctx['course_title']}",
            "message": lambda ctx: f"Your enrollment in {ctx['course_title']} is confirmed.",
            "email_body": lambda ctx: (
                f"Hello {ctx['recipient_name']},\n\nYou are now enrolled in {ctx['course_title']}."
            ),
        },
        "CourseCompleted": {
            "notification_type": "course_completed",
            "in_app_pref": "course_completed_in_app",
            "email_pref": "course_completed_email",
            "title": lambda ctx: f"Congratulations on completing {ctx['course_title']}",
            "message": lambda ctx: (
                f"Certificate issued: {ctx['certificate_number']}"
                if ctx.get("certificate_number")
                else f"You completed {ctx['course_title']}."
            ),
            "email_body": lambda ctx: (
                f"Hello {ctx['recipient_name']},\n\n"
                f"Congratulations on completing {ctx['course_title']}. "
                f"Certificate number: {ctx.get('certificate_number') or 'pending'}"
            ),
        },
        "CoursePublished": {
            "notification_type": "course_published",
            "in_app_pref": "course_published_in_app",
            "email_pref": "course_published_email",
            "title": lambda ctx: f"Your course {ctx['course_title']} is live",
            "message": lambda ctx: (
                f"Publishing finished successfully for version {ctx.get('version_number') or 'latest'}."
            ),
            "email_body": lambda ctx: (
                f"Hello {ctx['recipient_name']},\n\nYour course {ctx['course_title']} is now live."
            ),
        },
        "CourseReady": {
            "notification_type": "course_published",
            "in_app_pref": "course_published_in_app",
            "email_pref": "course_published_email",
            "title": lambda ctx: f"Your course {ctx['course_title']} is live",
            "message": lambda ctx: "Publishing finished successfully.",
            "email_body": lambda ctx: (
                f"Hello {ctx['recipient_name']},\n\nYour course {ctx['course_title']} is now live."
            ),
        },
    }
    return templates.get(event_type)


def _resolve_recipient_id(event: DomainEvent) -> str | None:
    payload = event.payload
    for candidate in (
        payload.get("student_id"),
        payload.get("instructor_id"),
        payload.get("user_id"),
        event.actor_id,
    ):
        text = _opt_str(candidate)
        if text is not None:
            return text
    return None


def _notification_metadata(event: DomainEvent, context: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "course_id": context.get("course_id"),
        "version_id": context.get("version_id"),
        "certificate_id": context.get("certificate_id"),
        "occurred_at": event.occurred_at,
        "source_service": event.source_service,
    }


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
