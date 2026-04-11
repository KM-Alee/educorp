from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness probe — service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe — service is ready to accept traffic."""
    # TODO: Add dependency checks in later phases
    return {"status": "ready"}
