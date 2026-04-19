from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.assets import router as assets_router
from app.api.v1.courses import router as courses_router
from app.api.v1.modules import router as modules_router
from app.dependencies import get_minio, get_mongo_db, get_session
from app.config import settings
from educorp_common.telemetry import set_dependency_status

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
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        mongo_db = get_mongo_db()
        await mongo_db.command("ping")
        checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "error"

    try:
        minio = get_minio()
        await minio.bucket_exists(settings.minio_bucket)
        checks["minio"] = "ok"
    except Exception:
        checks["minio"] = "error"

    for dependency, value in checks.items():
        set_dependency_status(service="course-service", dependency=dependency, ok=value == "ok")

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


router.include_router(courses_router)
router.include_router(modules_router)
router.include_router(assets_router)
