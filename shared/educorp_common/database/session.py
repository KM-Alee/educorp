from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine as sa_create_async_engine,
)


def create_async_engine(url: str, **kwargs: object) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    defaults = {
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }
    defaults.update(kwargs)
    return sa_create_async_engine(url, **defaults)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
