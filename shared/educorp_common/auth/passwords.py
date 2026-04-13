from __future__ import annotations

import re

from passlib.context import CryptContext

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$")

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(password, password_hash)


def validate_password_complexity(password: str, min_length: int = 8) -> None:
    """Validate password complexity rules."""
    if len(password) < min_length or not PASSWORD_REGEX.match(password):
        raise ValueError(
            "Password must be at least 8 characters and include upper, lower, and digit."
        )
