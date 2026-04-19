from __future__ import annotations

from app.services.cache import normalize_question, question_cache_key


def test_normalize_question_compacts_whitespace():
    assert normalize_question("  Hello   World  ") == "hello world"


def test_question_cache_key_is_deterministic():
    key1 = question_cache_key("Hello", "course", "version")
    key2 = question_cache_key("hello ", "course", "version")
    assert key1 == key2
