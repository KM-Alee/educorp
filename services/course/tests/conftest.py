from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool, create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import get_current_user, get_minio, get_session
from app.main import create_app
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.database.base import Base

# Import models so metadata is populated
import app.models  # noqa: F401


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def db_engine():
    """In-memory SQLite async engine for tests (structural only)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Provide an async DB session with rollback."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def instructor_user() -> CurrentUser:
    return CurrentUser(
        id=str(uuid4()),
        email="instructor@test.com",
        roles=["instructor"],
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
def mock_minio() -> MagicMock:
    client = MagicMock()
    client.put_object = AsyncMock()
    client.presigned_get_object = AsyncMock(return_value="https://minio.test/presigned")
    client.remove_object = AsyncMock()
    client.bucket_exists = AsyncMock(return_value=True)
    client.make_bucket = AsyncMock()
    return client


def _make_auth_override(user: CurrentUser):
    async def _override():
        return user
    return _override


@pytest.fixture
async def instructor_client(app, db_session, instructor_user, mock_minio):
    """API client authenticated as an instructor."""
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _make_auth_override(instructor_user)
    app.dependency_overrides[get_minio] = lambda: mock_minio
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(app, db_session, admin_user, mock_minio):
    """API client authenticated as an admin."""
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _make_auth_override(admin_user)
    app.dependency_overrides[get_minio] = lambda: mock_minio
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def student_client(app, db_session, student_user, mock_minio):
    """API client authenticated as a student."""
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _make_auth_override(student_user)
    app.dependency_overrides[get_minio] = lambda: mock_minio
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(app, db_session, mock_minio, instructor_user):
    """Default API client (instructor) for backward compat."""
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = _make_auth_override(instructor_user)
    app.dependency_overrides[get_minio] = lambda: mock_minio
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF file for upload tests."""
    return b"%PDF-1.4 minimal test content for validation"


@pytest.fixture
def sample_txt_bytes() -> bytes:
    """Simple text file for upload tests."""
    return b"This is sample text content for testing."
