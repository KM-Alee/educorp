from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.enrollments import router as enrollments_router

router = APIRouter()

router.include_router(enrollments_router)


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    # TODO: Add dependency checks in later phases
    return {"status": "ready"}
