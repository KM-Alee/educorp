from __future__ import annotations

from app.services.token_utils import estimate_tokens, truncate_to_token_limit


def test_estimate_tokens_handles_empty():
    assert estimate_tokens("") == 0


def test_truncate_to_token_limit():
    text = "a" * 100
    truncated = truncate_to_token_limit(text, 10)
    assert len(truncated) == 40
