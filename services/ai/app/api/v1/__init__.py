from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.ask import router as ask_router
from app.api.v1.instructor import router as instructor_router
from app.dependencies import get_kafka_producer, get_mongo_db, get_qdrant, get_redis, get_session
from educorp_common.telemetry import set_dependency_status

router = APIRouter()

router.include_router(ask_router)
router.include_router(instructor_router)


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    qdrant: QdrantClient = Depends(get_qdrant),
    kafka_producer=Depends(get_kafka_producer),
) -> dict[str, object]:
    """Readiness probe — verify required dependencies are reachable."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    try:
        await mongo_db.command("ping")
        checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "error"

    try:
        qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "error"

    checks["kafka"] = "ok" if kafka_producer is not None else "unavailable"

    for dependency, value in checks.items():
        set_dependency_status(service="ai-service", dependency=dependency, ok=value == "ok")

    required = {name: checks[name] for name in ("postgres", "redis", "mongodb", "qdrant")}
    status_value = "ready" if all(value == "ok" for value in required.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}
