from __future__ import annotations

import pytest
from app.services.instructor_service import _require_retrieved_context

from educorp_common.errors import EduCorpError


def test_require_retrieved_context_returns_context_for_chunks():
    context = _require_retrieved_context(
        [
            {
                "module_title": "Intro",
                "asset_title": "Slides",
                "text": "JavaScript fundamentals.",
            }
        ],
        "course",
    )

    assert "JavaScript fundamentals." in context


def test_require_retrieved_context_raises_when_no_chunks():
    with pytest.raises(EduCorpError, match="No indexed content was found"):
        _require_retrieved_context([], "course")
