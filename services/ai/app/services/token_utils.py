from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~= 4 chars."""
    return max(1, len(text) // 4) if text else 0


def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or not text:
        return ""
    max_chars = max_tokens * 4
    return text[:max_chars]
