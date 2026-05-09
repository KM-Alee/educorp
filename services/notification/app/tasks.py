"""Celery tasks for the EduCorp notification service (stub until Phase 6)."""

from __future__ import annotations

import structlog

from app.celery_app import celery_app
from app.celery_task_dedup import mark_completed, should_skip_completed

logger = structlog.get_logger()


@celery_app.task(name="notifications.send_email", bind=True, max_retries=3)
def send_email_task(
    self,
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Send an email notification (stub — no email provider configured yet)."""
    task_id = getattr(self.request, "id", None)
    if should_skip_completed("send_email", task_id):
        logger.info("send_email_task_duplicate_skipped", task_id=task_id, to=to)
        return {"status": "duplicate_skipped", "to": to, "subject": subject}

    logger.info("send_email_task", to=to, subject=subject)
    mark_completed("send_email", task_id)
    return {"status": "queued", "to": to, "subject": subject}


@celery_app.task(name="notifications.send_in_app", bind=True, max_retries=3)
def send_in_app_task(
    self,
    user_id: str,
    title: str,
    message: str,
    metadata: dict | None = None,
) -> dict:
    """Create an in-app notification (stub — persistence to be added in Phase 6)."""
    task_id = getattr(self.request, "id", None)
    if should_skip_completed("send_in_app", task_id):
        logger.info("send_in_app_task_duplicate_skipped", task_id=task_id, user_id=user_id)
        return {"status": "duplicate_skipped", "user_id": user_id, "title": title}

    logger.info("send_in_app_task", user_id=user_id, title=title)
    mark_completed("send_in_app", task_id)
    return {"status": "queued", "user_id": user_id, "title": title}
