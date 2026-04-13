#!/usr/bin/env python3
"""Verify seed data was created."""
from __future__ import annotations

import asyncio
import os

from educorp_common.database.session import create_async_engine
from sqlalchemy import text

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://educorp:educorp_dev@localhost:15432/educorp",
)


async def verify() -> None:
    """Verify seed data."""
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        # Check roles
        result = await conn.execute(text("SELECT COUNT(*) FROM auth.roles"))
        role_count = result.scalar()
        print(f"✓ Roles created: {role_count}")

        # Check admin user
        result = await conn.execute(text("SELECT COUNT(*) FROM auth.users"))
        user_count = result.scalar()
        print(f"✓ Admin user created: {user_count}")

        # Check user roles
        result = await conn.execute(text("SELECT COUNT(*) FROM auth.user_roles"))
        user_role_count = result.scalar()
        print(f"✓ User role assignments: {user_role_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
