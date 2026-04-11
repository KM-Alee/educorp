from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from educorp_common.auth.dependencies import CurrentUser, get_current_user, require_roles

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def set_engine(engine: AsyncEngine) -> None:
    """Set the database engine (called during lifespan startup)."""
    global _engine, _session_factory
    _engine = engine
    from educorp_common.database.session import create_session_factory

    _session_factory = create_session_factory(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        yield session


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_session",
    "require_roles",
    "set_engine",
]
