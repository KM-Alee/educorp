from __future__ import annotations

from typing import Any, TypedDict

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError

from educorp_common.auth.tokens import decode_access_token
from educorp_common.config.base import BaseAppSettings
from educorp_common.errors import ForbiddenError, UnauthorizedError


class CurrentUser(TypedDict):
    """Current authenticated user."""

    id: str
    email: str
    roles: list[str]
    is_active: bool
    is_verified: bool


settings = BaseAppSettings()
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return decode_access_token(
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


def _payload_to_user(payload: dict[str, Any]) -> CurrentUser:
    return CurrentUser(
        id=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        roles=list(payload.get("roles", [])),
        is_active=bool(payload.get("is_active", True)),
        is_verified=bool(payload.get("is_verified", True)),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> CurrentUser:
    """Extract and validate the current user from the JWT token."""
    payload = _decode_token(credentials.credentials)
    return _payload_to_user(payload)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
) -> CurrentUser | None:
    """Return the current user if credentials are provided; otherwise None."""
    if credentials is None:
        return None
    payload = _decode_token(credentials.credentials)
    return _payload_to_user(payload)


def require_roles(*roles: str) -> Any:
    """Dependency factory that checks the current user has at least one of the required roles."""

    async def _check_roles(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        user_roles = current_user["roles"]
        if not any(role in user_roles for role in roles):
            raise ForbiddenError("Insufficient permissions")
        return current_user

    return _check_roles
