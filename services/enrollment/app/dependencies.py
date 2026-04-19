from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from educorp_common.auth.dependencies import CurrentUser, get_current_user, require_roles

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: Redis | None = None


def set_engine(engine: AsyncEngine) -> None:
    """Set the database engine (called during lifespan startup)."""
    global _engine, _session_factory
    _engine = engine
    from educorp_common.database.session import create_session_factory

    _session_factory = create_session_factory(engine)


def set_redis(client: Redis) -> None:
    """Set the Redis client (called during lifespan startup)."""
    global _redis
    _redis = client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        yield session


async def get_redis() -> Redis:
    """Provide the Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


async def require_internal_service(
    x_internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
) -> None:
    from app.config import settings

    if x_internal_service_token != settings.internal_service_token:
        raise HTTPException(status_code=403, detail="Forbidden")


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_redis",
    "get_session",
    "require_internal_service",
    "require_roles",
    "set_engine",
    "set_redis",
]
