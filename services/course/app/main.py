from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from miniopy_async import Minio
from motor.motor_asyncio import AsyncIOMotorClient

from app.api.v1 import router as v1_router
from app.config import settings
from educorp_common.database.session import create_async_engine
from educorp_common.errors import register_exception_handlers
from educorp_common.middleware.correlation import CorrelationIdMiddleware
from educorp_common.middleware.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("Starting service", service=settings.service_name)

    # PostgreSQL
    engine = create_async_engine(settings.database_url)
    from app.dependencies import set_engine, set_minio, set_mongo

    set_engine(engine)

    # MongoDB
    mongo_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_url)  # type: ignore[type-arg]
    mongo_db = mongo_client[settings.mongo_db]
    set_mongo(mongo_client, mongo_db)

    # MinIO
    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )
    set_minio(minio_client)

    # Ensure bucket exists
    if not await minio_client.bucket_exists(settings.minio_bucket):
        await minio_client.make_bucket(settings.minio_bucket)

    yield

    mongo_client.close()
    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp Course Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    async def root_health_live() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(v1_router, prefix="/api/v1/courses")
    register_exception_handlers(app)
    return app


app = create_app()
