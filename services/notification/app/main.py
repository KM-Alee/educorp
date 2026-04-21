from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.consumers import NotificationKafkaConsumer
from app.config import settings
from educorp_common.app_setup import configure_http_app
from educorp_common.database.session import create_async_engine, create_session_factory
from educorp_common.errors import register_exception_handlers
from educorp_common.middleware.logging import setup_logging
from educorp_common.telemetry import instrument_sqlalchemy

logger = structlog.get_logger()


async def _start_consumer(consumer: NotificationKafkaConsumer) -> None:
    try:
        await consumer.start()
    except Exception as exc:
        logger.warning("Notification Kafka consumer unavailable", exc_info=exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("Starting service", service=settings.service_name)

    engine = create_async_engine(settings.database_url)
    from app.dependencies import set_engine

    set_engine(engine)
    instrument_sqlalchemy(engine)

    session_factory = create_session_factory(engine)
    consumer: NotificationKafkaConsumer | None = None
    consumer_task: asyncio.Task[None] | None = None
    try:
        consumer = NotificationKafkaConsumer(session_factory)
        consumer_task = asyncio.create_task(_start_consumer(consumer))
    except Exception as exc:
        logger.warning("Notification Kafka consumer unavailable", exc_info=exc)
        consumer = None

    yield

    if consumer_task is not None:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    if consumer is not None:
        await consumer.stop()
    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp Notification Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    async def root_health_live() -> dict[str, str]:
        return {"status": "ok"}

    configure_http_app(app, settings)
    app.include_router(v1_router, prefix="/api/v1/notifications")
    register_exception_handlers(app)
    return app


app = create_app()
