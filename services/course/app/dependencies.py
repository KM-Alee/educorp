from __future__ import annotations

from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from miniopy_async import Minio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from educorp_common.auth.dependencies import (
    CurrentUser,
    get_current_user,
    get_optional_user,
    require_roles,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_mongo_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_mongo_db: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]
_minio_client: Minio | None = None


def set_engine(engine: AsyncEngine) -> None:
    """Set the database engine (called during lifespan startup)."""
    global _engine, _session_factory
    _engine = engine
    from educorp_common.database.session import create_session_factory

    _session_factory = create_session_factory(engine)


def set_mongo(client: AsyncIOMotorClient, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
    """Set the MongoDB client and database (called during lifespan startup)."""
    global _mongo_client, _mongo_db
    _mongo_client = client
    _mongo_db = db


def set_minio(client: Minio) -> None:
    """Set the MinIO client (called during lifespan startup)."""
    global _minio_client
    _minio_client = client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        yield session


def get_mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Provide the MongoDB database handle."""
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized")
    return _mongo_db


def get_minio() -> Minio:
    """Provide the MinIO client."""
    if _minio_client is None:
        raise RuntimeError("MinIO not initialized")
    return _minio_client


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_optional_user",
    "get_minio",
    "get_mongo_db",
    "get_session",
    "require_roles",
    "set_engine",
    "set_minio",
    "set_mongo",
]
