from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_role_repository import UserRoleRepository
from educorp_common.auth.dependencies import CurrentUser
from educorp_common.auth.tokens import decode_access_token
from educorp_common.database.session import create_session_factory
from educorp_common.errors import ForbiddenError, UnauthorizedError

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: Redis | None = None
security = HTTPBearer()


def set_engine(engine: AsyncEngine) -> None:
    """Set the database engine (called during lifespan startup)."""
    global _engine, _session_factory
    _engine = engine
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
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


async def require_internal_service(
    x_internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
) -> None:
    if x_internal_service_token != settings.internal_service_token:
        raise HTTPException(status_code=403, detail="Forbidden")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = decode_access_token(
            token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except ExpiredSignatureError as exc:
        raise UnauthorizedError("Token expired") from exc
    except JWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    try:
        user_id = UUID(payload.get("sub", ""))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid token") from exc
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Invalid token")
    if not user.is_active:
        raise ForbiddenError("Account is inactive")
    if not user.is_verified:
        raise ForbiddenError("Email is not verified")

    role_ids = await UserRoleRepository(session).list_roles_for_user(user_id)
    roles = await RoleRepository(session).list_by_ids(role_ids)

    return CurrentUser(
        id=str(user.id),
        email=user.email,
        roles=[role.name for role in roles],
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


def require_roles(*roles: str):
    async def _check_roles(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not any(role in current_user["roles"] for role in roles):
            raise ForbiddenError("Insufficient permissions")
        return current_user

    return _check_roles


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_session",
    "get_redis",
    "require_internal_service",
    "require_roles",
    "set_engine",
    "set_redis",
]
