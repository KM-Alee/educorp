from __future__ import annotations

import pytest

from educorp_common.auth import hash_password, validate_password_complexity, verify_password


def test_hash_password_creates_hash() -> None:
    hashed = hash_password("ValidPass123")
    assert hashed.startswith("$argon2")


def test_verify_password_matches() -> None:
    hashed = hash_password("ValidPass123")
    assert verify_password("ValidPass123", hashed) is True


def test_validate_password_complexity_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_password_complexity("short")


def test_validate_password_complexity_accepts_valid() -> None:
    validate_password_complexity("ValidPass123")
