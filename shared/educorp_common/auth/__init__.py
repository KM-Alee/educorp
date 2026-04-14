from __future__ import annotations

from educorp_common.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_token,
    verify_refresh_token,
)


def hash_password(password: str) -> str:
    from educorp_common.auth.passwords import hash_password as _hash_password

    return _hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    from educorp_common.auth.passwords import verify_password as _verify_password

    return _verify_password(password, password_hash)


def validate_password_complexity(password: str, min_length: int = 8) -> None:
    from educorp_common.auth.passwords import (
        validate_password_complexity as _validate_password_complexity,
    )

    _validate_password_complexity(password, min_length)

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "hash_password",
    "hash_token",
    "validate_password_complexity",
    "verify_password",
    "verify_refresh_token",
]
