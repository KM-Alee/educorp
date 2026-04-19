from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.dependencies import get_current_user, get_session
from app.main import create_app
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.database.base import Base


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs) -> str:
    return "JSON"


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
        await conn.execute(text("ATTACH DATABASE ':memory:' AS progress"))
        await conn.execute(text("ATTACH DATABASE ':memory:' AS enrollment"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS enrollment.enrollments (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
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
async def api_client(app, db_session, student_user):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _override_user(student_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(app, db_session, admin_user):
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _override_user(admin_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
