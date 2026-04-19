from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.consumers import AnalyticsKafkaConsumer
from app.config import settings
from educorp_common.database.session import create_async_engine, create_session_factory
from educorp_common.errors import register_exception_handlers
from educorp_common.middleware.correlation import CorrelationIdMiddleware
from educorp_common.middleware.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("Starting service", service=settings.service_name)

    engine = create_async_engine(settings.database_url)
    from app.dependencies import set_engine

    set_engine(engine)

    session_factory = create_session_factory(engine)
    consumer: AnalyticsKafkaConsumer | None = None
    try:
        consumer = AnalyticsKafkaConsumer(session_factory)
        await consumer.start()
    except Exception as exc:
        logger.warning("Analytics Kafka consumer unavailable", exc_info=exc)
        consumer = None

    yield

    if consumer is not None:
        await consumer.stop()
    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp Analytics Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    async def root_health_live() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(v1_router, prefix="/api/v1/analytics")
    register_exception_handlers(app)
    return app


app = create_app()
