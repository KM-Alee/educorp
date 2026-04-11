from __future__ import annotations

from typing import Any, TypedDict

from fastapi import Depends, HTTPException, Request, status


class CurrentUser(TypedDict):
    """Current authenticated user."""

    id: str
    email: str
    roles: list[str]
    is_active: bool


async def get_current_user(request: Request) -> CurrentUser:
    """Extract and validate the current user from the JWT token.

    Stub implementation for Phase 0 — returns a mock user.
    Will be replaced with real JWT validation in Phase 1.
    """
    # Phase 0 stub: return a mock user
    return CurrentUser(
        id="00000000-0000-0000-0000-000000000001",
        email="dev@educorp.dev",
        roles=["admin", "instructor", "student"],
        is_active=True,
    )


def require_roles(*roles: str) -> Any:
    """Dependency factory that checks the current user has at least one of the required roles."""

    async def _check_roles(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        user_roles = current_user["roles"]
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return Depends(_check_roles)
