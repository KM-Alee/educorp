from __future__ import annotations

"""
Celery application for the EduCorp notification worker.

The broker URL falls back to the RabbitMQ default used in docker-compose.
Set CELERY_BROKER_URL and CELERY_RESULT_BACKEND environment variables
to override in production.
"""

import os

from celery import Celery

BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://educorp:educorp_dev@rabbitmq:5672//",
)
RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://:educorp_dev@redis:6379/1",
)

celery_app = Celery(
    "notification",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
