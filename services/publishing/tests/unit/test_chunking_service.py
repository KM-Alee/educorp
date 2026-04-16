from __future__ import annotations

import pytest

from app.services.canonical_builder import build_canonical_page
from app.services.chunking_service import ChunkingService, _detect_boilerplate


def _page(
    page_num: int,
    text: str,
    *,
    asset_id: str = "asset-1",
    version_id: str = "ver-1",
    module_id: str = "mod-1",
    module_title: str = "Module",
    asset_title: str = "Lecture",
    source_type: str = "pdf",
    confidence: float = 0.95,
):
    return build_canonical_page(
        version_id=version_id,
        asset_id=asset_id,
        source_type=source_type,
        page_or_slide_number=page_num,
        module_id=module_id,
        module_title=module_title,
        asset_title=asset_title,
        native_text=text,
        text_confidence=confidence,
    )


class TestChunkingServiceSplitPages:
    def setup_method(self) -> None:
        self.svc = ChunkingService(
            chunk_target_tokens=100,  # small for test (≈ 400 chars)
            chunk_max_tokens=150,
            chunk_overlap_tokens=10,
        )

    def test_empty_pages_returns_no_chunks(self) -> None:
        chunks, stats = self.svc.split_pages([], course_id="c1")
        assert chunks == []
        assert stats.total_chunks == 0

    def test_single_short_page_one_chunk(self) -> None:
        pages = [_page(1, "This is a short page with a few words.")]
        chunks, stats = self.svc.split_pages(pages, course_id="c1")
        assert len(chunks) == 1
        assert stats.total_chunks == 1
        assert chunks[0].page_or_slide_number == 1

    def test_chunk_carries_provenance(self) -> None:
        pages = [_page(3, "Content for page three.", asset_id="a42", module_id="m99")]
        chunks, _ = self.svc.split_pages(pages, course_id="course-abc")
        c = chunks[0]
        assert c.asset_id == "a42"
        assert c.module_id == "m99"
        assert c.page_or_slide_number == 3
        assert c.course_id == "course-abc"
        assert c.version_id == "ver-1"
        assert c.source_type == "pdf"

    def test_chunk_has_hash(self) -> None:
        pages = [_page(1, "Some content for hashing.")]
        chunks, _ = self.svc.split_pages(pages, course_id="c1")
        assert len(chunks[0].chunk_hash) == 64

    def test_duplicate_chunks_detected(self) -> None:
        # Same page twice (same version_id + asset_id + page_num → same hash)
        text = "Identical content on both pages."
        pages = [
            _page(1, text),
            _page(1, text),  # duplicate page number → same hash
        ]
        chunks, stats = self.svc.split_pages(pages, course_id="c1")
        assert stats.duplicate_chunks_removed >= 1

    def test_long_page_split_into_multiple_chunks(self) -> None:
        # Create text clearly larger than chunk_max_tokens (150 * 4 = 600 chars)
        long_text = ("word " * 200).strip()
        pages = [_page(1, long_text)]
        chunks, stats = self.svc.split_pages(pages, course_id="c1")
        assert len(chunks) > 1
        assert all(c.page_or_slide_number == 1 for c in chunks)
        # Chunks should not exceed hard cap
        max_chars = 150 * 4  # chunk_max_tokens * chars_per_token
        assert all(len(c.text) <= max_chars + 100 for c in chunks)  # small tolerance

    def test_empty_page_text_skipped(self) -> None:
        pages = [_page(1, ""), _page(2, "  "), _page(3, "Real content here")]
        chunks, _ = self.svc.split_pages(pages, course_id="c1")
        assert len(chunks) == 1
        assert chunks[0].page_or_slide_number == 3

    def test_quality_score_propagated(self) -> None:
        pages = [_page(1, "content", confidence=0.42)]
        chunks, _ = self.svc.split_pages(pages, course_id="c1")
        assert abs(chunks[0].quality_score - 0.42) < 0.01

    def test_module_and_asset_titles_propagated(self) -> None:
        pages = [_page(1, "content", module_title="Deep Learning", asset_title="Week 5")]
        chunks, _ = self.svc.split_pages(pages, course_id="c1")
        assert chunks[0].module_title == "Deep Learning"
        assert chunks[0].asset_title == "Week 5"


class TestBoilerplateDetection:
    def test_repeated_short_line_detected(self) -> None:
        pages = [_page(i, f"Real content {i}\nCopyright 2024") for i in range(1, 8)]
        boilerplate = _detect_boilerplate(pages)
        assert "Copyright 2024" in boilerplate

    def test_unique_lines_not_detected(self) -> None:
        pages = [_page(i, f"Unique content line {i}") for i in range(1, 8)]
        boilerplate = _detect_boilerplate(pages)
        assert all(f"Unique content line {i}" not in boilerplate for i in range(1, 8))

    def test_fewer_than_three_pages_no_boilerplate(self) -> None:
        pages = [_page(1, "Line\nCopyright 2024"), _page(2, "Other\nCopyright 2024")]
        boilerplate = _detect_boilerplate(pages)
        assert boilerplate == set()
