#!/usr/bin/env python3
"""Generate service skeleton files for all 9 EduCorp services."""
import os
from pathlib import Path

BASE = Path("/home/kali/proj/educorp")

SERVICES = {
    "auth":         {"title": "Auth",         "port": 8001, "api_prefix": "auth"},
    "course":       {"title": "Course",       "port": 8002, "api_prefix": "courses"},
    "enrollment":   {"title": "Enrollment",   "port": 8003, "api_prefix": "enrollments"},
    "progress":     {"title": "Progress",     "port": 8004, "api_prefix": "progress"},
    "publishing":   {"title": "Publishing",   "port": 8005, "api_prefix": "publishing"},
    "ai":           {"title": "AI",           "port": 8006, "api_prefix": "ai"},
    "search":       {"title": "Search",       "port": 8007, "api_prefix": "search"},
    "notification": {"title": "Notification", "port": 8008, "api_prefix": "notifications"},
    "analytics":    {"title": "Analytics",    "port": 8009, "api_prefix": "analytics"},
}

# Services that need DB (have alembic)
DB_SERVICES = {"auth", "course", "enrollment", "progress", "publishing", "notification", "analytics"}

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  Created {path.relative_to(BASE)}")

for name, meta in SERVICES.items():
    svc_dir = BASE / "services" / name
    title = meta["title"]
    port = meta["port"]
    api_prefix = meta["api_prefix"]

    # config.py
    write(svc_dir / "app" / "config.py", f'''from __future__ import annotations

from educorp_common.config.base import BaseAppSettings


class Settings(BaseAppSettings):
    """{title} service settings."""

    service_name: str = "{name}-service"
    service_port: int = {port}


settings = Settings()
''')

    # dependencies.py
    write(svc_dir / "app" / "dependencies.py", '''from __future__ import annotations

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
''')

    # api/v1/__init__.py
    write(svc_dir / "app" / "api" / "v1" / "__init__.py", '''from __future__ import annotations

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
''')

    # main.py
    write(svc_dir / "app" / "main.py", f'''from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.config import settings
from educorp_common.database.session import create_async_engine
from educorp_common.errors import register_exception_handlers
from educorp_common.middleware.correlation import CorrelationIdMiddleware
from educorp_common.middleware.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(settings.log_level)
    logger.info("Starting service", service=settings.service_name)

    engine = create_async_engine(settings.database_url)
    from app.dependencies import set_engine

    set_engine(engine)

    yield

    await engine.dispose()
    logger.info("Service stopped", service=settings.service_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="EduCorp {title} Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(v1_router, prefix="/api/v1/{api_prefix}")
    register_exception_handlers(app)
    return app


app = create_app()
''')

    # worker stub for publishing
    if name == "publishing":
        write(svc_dir / "app" / "worker.py", '''from __future__ import annotations

"""Temporal worker stub for Phase 0. Will be implemented in Phase 3."""


async def main() -> None:
    """Start the Temporal worker."""
    print("Publishing worker stub — will be implemented in Phase 3")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
''')

    # tests/conftest.py
    write(svc_dir / "tests" / "conftest.py", f'''from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def api_client(app):
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
''')

    # Alembic setup for DB services
    if name in DB_SERVICES:
        write(svc_dir / "alembic.ini", f'''[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://educorp:educorp_dev@postgres:5432/educorp

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''')

        write(svc_dir / "alembic" / "env.py", f'''from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from educorp_common.database.base import Base

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
        include_schemas=True,
        version_table_schema="{name}",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="{name}",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in online mode (async)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
''')

        write(svc_dir / "alembic" / "script.py.mako", '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
''')

        write(svc_dir / "alembic" / "versions" / ".gitkeep", "")

    print(f"Completed: {name}")

print("\nAll 9 service skeletons generated!")
