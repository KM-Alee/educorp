from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.search import router as search_router
from app.dependencies import get_session
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

    for dependency, value in checks.items():
        set_dependency_status(service="search-service", dependency=dependency, ok=value == "ok")

    status_value = "ready" if all(value == "ok" for value in checks.values()) else "degraded"
    if status_value != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": status_value, "checks": checks}


router.include_router(search_router)
