from __future__ import annotations

"""Temporal worker for the publishing pipeline."""

import asyncio

import structlog
from miniopy_async import Minio
from temporalio.client import Client
from temporalio.worker import Worker

from app.activities.publishing_activities import PublishingActivities
from app.config import settings
from app.workflows.publish_course import PublishCourseWorkflow
from educorp_common.database.session import create_async_engine, create_session_factory
from educorp_common.middleware.logging import setup_logging

logger = structlog.get_logger()


async def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Starting publishing worker")

    engine = create_async_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )

    temporal = await Client.connect(
        f"{settings.temporal_host}:{settings.temporal_port}",
        namespace=settings.temporal_namespace,
    )

    activities = PublishingActivities(
        session_factory=session_factory,
        minio_client=minio_client,
    )

    worker = Worker(
        temporal,
        task_queue=settings.temporal_task_queue,
        workflows=[PublishCourseWorkflow],
        activities=[
            activities.preflight_review,
            activities.mark_version_publishing,
            activities.extract_text,
            activities.chunk_content,
            activities.generate_embeddings,
            activities.index_qdrant,
            activities.finalize_version,
            activities.mark_version_rejected,
            activities.mark_version_failed,
        ],
    )

    await worker.run()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
