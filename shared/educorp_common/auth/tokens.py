from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import jwt


def create_access_token(
    *,
    subject: str,
    email: str,
    roles: list[str],
    secret_key: str,
    algorithm: str,
    issuer: str,
    audience: str,
    expires_delta: timedelta,
) -> str:
    """Create a signed access token."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid4()),
        "iss": issuer,
        "aud": audience,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str,
    issuer: str,
    audience: str,
) -> dict[str, Any]:
    """Decode and validate an access token."""
    return jwt.decode(
        token,
        secret_key,
        algorithms=[algorithm],
        issuer=issuer,
        audience=audience,
    )


def hash_token(raw_token: str) -> str:
    """Hash a token using SHA-256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token() -> tuple[str, str]:
    """Create a refresh token and its hash."""
    raw_token = secrets.token_urlsafe(48)
    return raw_token, hash_token(raw_token)


def verify_refresh_token(raw_token: str, stored_hash: str) -> bool:
    """Verify a refresh token against a stored hash."""
    return hash_token(raw_token) == stored_hash
