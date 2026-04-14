from __future__ import annotations

"""
Celery tasks for the EduCorp notification service.
Placeholder implementation — tasks will be fleshed out in Phase 6.
"""

import structlog

from app.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="notifications.send_email", bind=True, max_retries=3)
def send_email_task(
    self,  # noqa: ANN001
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Send an email notification (stub — no email provider configured yet)."""
    logger.info("send_email_task", to=to, subject=subject)
    return {"status": "queued", "to": to, "subject": subject}


@celery_app.task(name="notifications.send_in_app", bind=True, max_retries=3)
def send_in_app_task(
    self,  # noqa: ANN001
    user_id: str,
    title: str,
    message: str,
    metadata: dict | None = None,
) -> dict:
    """Create an in-app notification (stub — persistence to be added in Phase 6)."""
    logger.info("send_in_app_task", user_id=user_id, title=title)
    return {"status": "queued", "user_id": user_id, "title": title}
