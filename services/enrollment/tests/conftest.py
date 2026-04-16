from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.dependencies import get_current_user, get_redis, get_session
from app.main import create_app
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.database.base import Base


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._store.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        _ = ex
        async with self._lock:
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

    async def delete(self, key: str) -> int:
        async with self._lock:
            existed = key in self._store
            self._store.pop(key, None)
            return 1 if existed else 0


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.execute(text("ATTACH DATABASE ':memory:' AS enrollment"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(db_session_factory):
    async with db_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def student_user() -> CurrentUser:
    return CurrentUser(
        id=str(uuid4()),
        email="student@test.com",
        roles=["student"],
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def admin_user() -> CurrentUser:
    return CurrentUser(
        id=str(uuid4()),
        email="admin@test.com",
        roles=["admin"],
        is_active=True,
        is_verified=True,
    )


def _override_user(user: CurrentUser):
    async def _inner() -> CurrentUser:
        return user

    return _inner


@pytest.fixture
async def api_client(app, db_session, fake_redis, student_user):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_current_user] = _override_user(student_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(app, db_session, fake_redis, admin_user):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_current_user] = _override_user(admin_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
