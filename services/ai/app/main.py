from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from aiokafka import AIOKafkaProducer

from app.api.v1 import router as v1_router
from app.config import settings
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
    from app.dependencies import (
        set_engine,
        set_kafka_producer,
        set_mongo,
        set_qdrant,
        set_redis,
    )

    set_engine(engine)
    instrument_sqlalchemy(engine)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    set_redis(redis)

    mongo_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_url)  # type: ignore[type-arg]
    mongo_db = mongo_client[settings.mongo_db]
    set_mongo(mongo_client, mongo_db)

    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    set_qdrant(qdrant)

    kafka_producer: AIOKafkaProducer | None = None
    try:
        kafka_producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        await kafka_producer.start()
        set_kafka_producer(kafka_producer)
    except Exception as exc:
        logger.warning("Kafka producer unavailable", exc_info=exc)
        kafka_producer = None

    try:
        from app.services.instructor_service import InstructorService

        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            service = InstructorService(
                session=session,
                redis=redis,
                qdrant=qdrant,
                mongo_db=mongo_db,
                kafka_producer=kafka_producer,
            )
            await service.reconcile_orphaned_jobs()
    except Exception as exc:
        logger.warning("Instructor job reconciliation failed", exc_info=exc)

    yield

    if kafka_producer is not None:
        await kafka_producer.stop()
    mongo_client.close()
    await redis.close()
    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp AI Service",
        version="0.1.0",
        docs_url="/api/v1/ai/docs",
        openapi_url="/api/v1/ai/openapi.json",
        redoc_url="/api/v1/ai/redoc",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    async def root_health_live() -> dict[str, str]:
        return {"status": "ok"}

    configure_http_app(app, settings)
    app.include_router(v1_router, prefix="/api/v1/ai")
    register_exception_handlers(app)
    return app


app = create_app()
