from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.ask import router as ask_router
from app.api.v1.instructor import router as instructor_router

router = APIRouter()

router.include_router(ask_router)
router.include_router(instructor_router)


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    # TODO: Add dependency checks in later phases
    return {"status": "ready"}
