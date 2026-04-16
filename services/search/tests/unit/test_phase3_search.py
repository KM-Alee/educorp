"""Phase 3 search tests: keyword FTS scoring, semantic citation fields."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.search import SemanticChunkResult
from app.services.keyword_search_service import KeywordSearchService, _score, _matched_fields


# ---------------------------------------------------------------------------
# Keyword search service scoring
# ---------------------------------------------------------------------------


class TestKeywordSearchScoring:
    def test_title_match_high_score(self) -> None:
        row = {"title": "JavaScript Closures", "short_description": "A deep dive"}
        matched = _matched_fields("javascript", row, ts_rank=0.1)
        assert "title" in matched
        score = _score(0.1, matched)
        assert score > 0.7

    def test_no_query_returns_half(self) -> None:
        score = _score(0.0, [])
        assert score == 0.5

    def test_ts_rank_boosts_score(self) -> None:
        matched = ["title"]
        low_score = _score(0.01, matched)
        high_score = _score(0.5, matched)
        assert high_score > low_score

    def test_score_capped_at_one(self) -> None:
        score = _score(10.0, ["title"])
        assert score <= 0.99

    def test_content_fallback_matched(self) -> None:
        row = {"title": "Different title", "short_description": "Other"}
        matched = _matched_fields("asyncio", row, ts_rank=0.3)
        assert "content" in matched

    def test_tags_matched(self) -> None:
        row = {"title": "Course", "short_description": "", "tags": ["javascript", "web"]}
        matched = _matched_fields("javascript", row, ts_rank=0.0)
        assert "tags" in matched

    def test_empty_query_no_matches(self) -> None:
        row = {"title": "JavaScript", "short_description": "JS basics"}
        matched = _matched_fields("", row, ts_rank=0.0)
        assert matched == []


# ---------------------------------------------------------------------------
# SemanticChunkResult citation fields
# ---------------------------------------------------------------------------


class TestSemanticChunkResultSchema:
    def _make_chunk(self, **override) -> SemanticChunkResult:
        defaults = dict(
            chunk_id=str(uuid4()),
            course_id=uuid4(),
            version_id=uuid4(),
            text="The closure captures its lexical scope.",
            score=0.87,
            module_id=uuid4(),
            module_title="Lecture 7 - Closures",
            asset_id=uuid4(),
            asset_title="Lecture 7-Javascript.pdf",
            page_or_slide_number=12,
            chunk_index=2,
            quality_score=0.91,
        )
        defaults.update(override)
        return SemanticChunkResult(**defaults)

    def test_all_citation_fields_present(self) -> None:
        chunk = self._make_chunk()
        assert chunk.course_id is not None
        assert chunk.version_id is not None
        assert chunk.module_title == "Lecture 7 - Closures"
        assert chunk.asset_title == "Lecture 7-Javascript.pdf"
        assert chunk.page_or_slide_number == 12
        assert chunk.quality_score == pytest.approx(0.91)

    def test_page_or_slide_number_optional(self) -> None:
        chunk = self._make_chunk(page_or_slide_number=None)
        assert chunk.page_or_slide_number is None

    def test_quality_score_optional(self) -> None:
        chunk = self._make_chunk(quality_score=None)
        assert chunk.quality_score is None

    def test_chunk_id_is_string(self) -> None:
        # chunk_id is str (Qdrant UUID may be non-standard)
        chunk = self._make_chunk(chunk_id="custom-id-123")
        assert chunk.chunk_id == "custom-id-123"
