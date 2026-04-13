from __future__ import annotations

from datetime import timedelta

from app.config import settings
from educorp_common.auth import create_access_token, decode_access_token


def test_create_and_decode_access_token() -> None:
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        email="test@example.com",
        roles=["student"],
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(minutes=5),
    )

    payload = decode_access_token(
        token,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["email"] == "test@example.com"
    assert payload["roles"] == ["student"]
