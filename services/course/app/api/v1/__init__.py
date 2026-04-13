from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.courses import router as courses_router
from app.api.v1.modules import router as modules_router

router = APIRouter()


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    return {"status": "ready"}


router.include_router(courses_router)
router.include_router(modules_router)
router.include_router(assets_router)
