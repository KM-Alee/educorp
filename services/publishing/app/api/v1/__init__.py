from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from miniopy_async import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.config import settings
from app.dependencies import get_session
from app.api.v1.versions import router as versions_router
from app.services.qdrant_service import QdrantService

router = APIRouter()


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Readiness probe — verify required dependencies are reachable."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        temporal = await Client.connect(
            f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        await temporal.service_client.check_health()
        checks["temporal"] = "ok"
    except Exception:
        checks["temporal"] = "error"

    try:
        qdrant = QdrantService()
        qdrant._client.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "error"

    try:
        minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        await minio_client.bucket_exists(settings.minio_bucket)
        checks["minio"] = "ok"
    except Exception:
        checks["minio"] = "error"

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


router.include_router(versions_router)
