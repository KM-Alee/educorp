from __future__ import annotations

from app.services.canonical_builder import (
    CanonicalPageRecord,
    build_canonical_page,
    compute_content_hash,
)


def _make_page(**overrides) -> CanonicalPageRecord:
    defaults = dict(
        version_id="v1",
        asset_id="a1",
        source_type="pdf",
        page_or_slide_number=1,
        module_id="m1",
        module_title="Module 1",
        asset_title="Lecture 1",
        native_text="This is native lecture content about machine learning.",
        text_confidence=0.95,
    )
    defaults.update(overrides)
    return build_canonical_page(**defaults)


class TestComputeContentHash:
    def test_same_text_same_hash(self) -> None:
        h1 = compute_content_hash("Hello World")
        h2 = compute_content_hash("Hello World")
        assert h1 == h2

    def test_case_insensitive(self) -> None:
        assert compute_content_hash("Hello World") == compute_content_hash("hello world")

    def test_whitespace_collapsed(self) -> None:
        assert compute_content_hash("hello   world") == compute_content_hash("hello world")

    def test_different_text_different_hash(self) -> None:
        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_empty_string(self) -> None:
        h = compute_content_hash("")
        assert isinstance(h, str)
        assert len(h) == 64


class TestBuildCanonicalPage:
    def test_basic_build(self) -> None:
        page = _make_page()
        assert page.version_id == "v1"
        assert page.native_text.startswith("This is native")
        assert page.text_confidence == 0.95

    def test_content_hash_is_set(self) -> None:
        page = _make_page()
        assert len(page.content_hash) == 64

    def test_content_hash_deterministic(self) -> None:
        p1 = _make_page()
        p2 = _make_page()
        assert p1.content_hash == p2.content_hash

    def test_flags_default_empty(self) -> None:
        page = _make_page()
        assert page.flags == []

    def test_ocr_flag_stored(self) -> None:
        page = _make_page(flags=["ocr_rescue", "image_heavy"])
        assert "ocr_rescue" in page.flags


class TestCanonicalPageMethods:
    def test_merged_text_native_only(self) -> None:
        page = _make_page(native_text="sample text")
        assert "sample text" in page.merged_text()

    def test_merged_text_includes_ocr(self) -> None:
        page = _make_page(
            native_text="",
            ocr_text="ocr extracted text",
        )
        assert "ocr extracted text" in page.merged_text()

    def test_merged_text_includes_visual(self) -> None:
        page = _make_page(
            native_text="",
            ocr_text="",
            visual_summary="Diagram of neural network layers",
            has_visual_summary=True,
        )
        assert "Diagram of neural network" in page.merged_text()

    def test_merged_text_deduplicates_same_native_ocr(self) -> None:
        text = "exact same text"
        page = _make_page(native_text=text, ocr_text=text)
        # Should only appear once (ocr_text stripped when identical to native_text)
        merged = page.merged_text()
        assert merged.count(text) == 1

    def test_content_sources_native_only(self) -> None:
        page = _make_page(native_text="text", ocr_text="", visual_summary="")
        assert page.content_sources_used() == ["native_text"]

    def test_content_sources_with_ocr(self) -> None:
        page = _make_page(native_text="text", ocr_text="ocr")
        assert "ocr_text" in page.content_sources_used()

    def test_quality_score_high_confidence(self) -> None:
        page = _make_page(text_confidence=0.95)
        assert page.quality_score() >= 0.9

    def test_quality_score_empty_page(self) -> None:
        page = _make_page(native_text="", ocr_text="", visual_summary="")
        assert page.quality_score() == 0.0

    def test_to_dict_includes_merged_text(self) -> None:
        page = _make_page(native_text="test content")
        d = page.to_dict()
        assert "merged_text" in d
        assert "content_sources_used" in d
        assert "quality_score" in d
