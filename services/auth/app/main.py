from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.v1 import router as v1_router
from app.config import settings
from app.relay import AuthOutboxRelay
from educorp_common.app_setup import configure_http_app
from educorp_common.database.session import create_async_engine, create_session_factory
from educorp_common.errors import register_exception_handlers
from educorp_common.middleware.logging import setup_logging
from educorp_common.telemetry import instrument_sqlalchemy

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("Starting service", service=settings.service_name)

    engine = create_async_engine(settings.database_url)
    from app.dependencies import set_engine

    set_engine(engine)
    instrument_sqlalchemy(engine)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    from app.dependencies import set_redis

    set_redis(redis)

    session_factory = create_session_factory(engine)
    relay: AuthOutboxRelay | None = None
    try:
        relay = AuthOutboxRelay(session_factory)
        await relay.start()
    except Exception as exc:
        logger.warning("Auth outbox relay unavailable", exc_info=exc)
        relay = None

    yield

    if relay is not None:
        await relay.stop()
    await redis.close()
    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp Auth Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/auth/docs",
        redoc_url="/api/v1/auth/redoc",
        openapi_url="/api/v1/auth/openapi.json",
    )

    @app.get("/health/live")
    async def root_health_live() -> dict[str, str]:
        return {"status": "ok"}

    configure_http_app(app, settings)
    app.include_router(v1_router, prefix="/api/v1/auth")
    register_exception_handlers(app)
    return app


app = create_app()
