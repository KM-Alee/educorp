from __future__ import annotations

import asyncio
import os

from educorp_common.auth import hash_password
from educorp_common.database.session import create_async_engine, create_session_factory

from app.config import settings
from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_role_repository import UserRoleRepository

DEFAULT_ROLES = ["student", "instructor", "admin"]


def get_admin_credentials() -> tuple[str, str]:
    email = os.getenv("ADMIN_EMAIL", "admin@educorp.dev")
    password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
    return email, password


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        roles_repo = RoleRepository(session)
        user_roles_repo = UserRoleRepository(session)
        users_repo = UserRepository(session)

        roles: dict[str, Role] = {}
        for role_name in DEFAULT_ROLES:
            role = await roles_repo.get_by_name(role_name)
            if role is None:
                role = await roles_repo.create(
                    Role(name=role_name, description=f"Default {role_name} role")
                )
            roles[role_name] = role

        admin_email, admin_password = get_admin_credentials()
        admin_user = await users_repo.get_by_email(admin_email)
        if admin_user is None:
            admin_user = User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                first_name="Admin",
                last_name="User",
                is_active=True,
                is_verified=True,
            )
            await users_repo.create(admin_user)

        for role in roles.values():
            await user_roles_repo.add_role(
                admin_user.id, role.id, granted_by=admin_user.id
            )

        await session.commit()

    await engine.dispose()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
