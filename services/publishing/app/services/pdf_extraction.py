from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.services.ocr_service import OCRService
    from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)

try:
    import fitz  # pymupdf

    _FITZ_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FITZ_AVAILABLE = False
    logger.warning("pymupdf (fitz) not available; PDF rendering disabled")

# Minimal raster-region area fraction to be considered "large"
_LARGE_RASTER_FRACTION = 0.15

# Repeated slide-number patterns stripped during heuristics
_SLIDE_NUM_RE = re.compile(r"^\s*\d{1,3}\s*$")
_HEADER_FOOTER_RES = [
    re.compile(r"^\s*(page|slide)\s+\d+(\s+of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*©\s*\d{4}", re.IGNORECASE),
    re.compile(r"^\s*confidential\s*$", re.IGNORECASE),
    re.compile(r"^\s*all rights reserved\s*$", re.IGNORECASE),
]


@dataclass
class PageHeuristics:
    page_number: int
    native_text_length: int
    text_block_count: int
    has_large_rasters: bool
    is_effectively_image_only: bool
    text_coverage_ratio: float
    confidence: float
    flags: list[str] = field(default_factory=list)


@dataclass
class PDFPageData:
    page_number: int
    native_text: str
    ocr_text: str
    visual_summary: str
    has_visual_summary: bool
    text_confidence: float
    visual_confidence: float
    heuristics: PageHeuristics
    flags: list[str]


class PDFExtractionPipeline:
    """
    Multi-stage PDF extraction pipeline.

    Stages per page:
    1. Native text extraction + heuristics
    2. OCR rescue (only for weak-text pages)
    3. NanoGPT visual enrichment (only for still-low-confidence image-heavy pages
       within the operator-configured budget)
    """

    def __init__(self, ocr_service: OCRService, vision_service: VisionService) -> None:
        self._ocr = ocr_service
        self._vision = vision_service

    async def extract(
        self,
        asset_id: str,
        data: bytes,
    ) -> tuple[list[PDFPageData], dict[str, int]]:
        """
        Extract all pages from a PDF.

        Returns ``(pages, stats)`` where ``stats`` has keys:
        ``total_pages``, ``ocr_pages``, ``nanogpt_pages``, ``low_confidence_pages``.
        """
        stats: dict[str, int] = {
            "total_pages": 0,
            "ocr_pages": 0,
            "nanogpt_pages": 0,
            "low_confidence_pages": 0,
        }

        if not _FITZ_AVAILABLE:
            logger.error("pymupdf unavailable; returning empty extraction for asset %s", asset_id)
            return [], stats

        doc = fitz.open(stream=data, filetype="pdf")  # type: ignore[attr-defined]
        pages: list[PDFPageData] = []
        nanogpt_count = 0
        max_nanogpt = settings.visual_enrichment_max_pages_per_asset

        try:
            for fitz_page in doc:
                page_num = fitz_page.number + 1
                stats["total_pages"] += 1

                heuristics = _compute_heuristics(fitz_page, page_num)
                native_text = _extract_native_text(fitz_page)
                ocr_text = ""
                visual_summary = ""
                has_visual_summary = False
                visual_confidence = 0.0
                flags = list(heuristics.flags)
                confidence = heuristics.confidence

                # ── Stage 2: OCR rescue ──────────────────────────────────────
                needs_ocr = len(native_text.strip()) < settings.low_text_threshold_chars
                if needs_ocr:
                    png_bytes = _render_page_png(fitz_page)
                    ocr_text = await self._ocr.extract_text(png_bytes)
                    ocr_confidence = await self._ocr.confidence(png_bytes)
                    stats["ocr_pages"] += 1
                    flags.append("ocr_rescue")
                    confidence = max(confidence, ocr_confidence)

                    # ── Stage 3: NanoGPT visual enrichment ──────────────────
                    budget_ok = (
                        settings.visual_enrichment_enabled
                        and nanogpt_count < max_nanogpt
                        and (nanogpt_count / stats["total_pages"])
                        < settings.visual_enrichment_max_percent_per_asset
                    )
                    if (
                        budget_ok
                        and heuristics.is_effectively_image_only
                        and ocr_confidence < settings.ocr_confidence_threshold
                    ):
                        result = await self._vision.enrich_page(png_bytes)
                        if result:
                            visual_summary = result.get("factual_summary", "")  # type: ignore[assignment]
                            terms = result.get("diagram_terms", [])
                            if terms:
                                visual_summary = (
                                    f"{visual_summary} Terms: {', '.join(terms)}".strip()  # type: ignore[arg-type]
                                )
                            has_visual_summary = bool(visual_summary)
                            visual_confidence = 0.70  # assume enriched page is usable
                            confidence = max(confidence, visual_confidence)
                            nanogpt_count += 1
                            stats["nanogpt_pages"] += 1
                            flags.append("visual_enrichment")
                    elif settings.visual_enrichment_enabled and not budget_ok:
                        flags.append("visual_budget_exceeded")

                if confidence < settings.visual_confidence_threshold:
                    stats["low_confidence_pages"] += 1
                    flags.append("low_confidence")

                pages.append(
                    PDFPageData(
                        page_number=page_num,
                        native_text=native_text,
                        ocr_text=ocr_text,
                        visual_summary=visual_summary,
                        has_visual_summary=has_visual_summary,
                        text_confidence=heuristics.confidence,
                        visual_confidence=visual_confidence,
                        heuristics=heuristics,
                        flags=flags,
                    )
                )
        finally:
            doc.close()

        return pages, stats


# ── Helpers ──────────────────────────────────────────────────────────────────


def _compute_heuristics(fitz_page: object, page_number: int) -> PageHeuristics:  # type: ignore[type-arg]
    flags: list[str] = []

    # Native text blocks
    blocks = fitz_page.get_text("blocks")  # type: ignore[attr-defined]
    text_blocks = [b for b in blocks if b[6] == 0]  # type=0 is text
    image_blocks = [b for b in blocks if b[6] == 1]  # type=1 is image

    native_text = " ".join(b[4] for b in text_blocks if b[4].strip())
    native_text_length = len(native_text.strip())
    text_block_count = len(text_blocks)

    # Page area for coverage ratio
    rect = fitz_page.rect  # type: ignore[attr-defined]
    page_area = max(1.0, rect.width * rect.height)

    # Text coverage via character/word bbox area (rough estimate)
    text_area = sum(abs((b[2] - b[0]) * (b[3] - b[1])) for b in text_blocks)
    text_coverage_ratio = min(1.0, text_area / page_area)

    # Large rasters: any image block covering > _LARGE_RASTER_FRACTION of page
    has_large_rasters = any(
        abs((b[2] - b[0]) * (b[3] - b[1])) / page_area > _LARGE_RASTER_FRACTION
        for b in image_blocks
    )

    is_effectively_image_only = (
        native_text_length < settings.low_text_threshold_chars and has_large_rasters
    )

    if has_large_rasters:
        flags.append("image_heavy")
    if is_effectively_image_only:
        flags.append("image_only")

    # Confidence heuristic: based on text coverage
    if native_text_length >= settings.low_text_threshold_chars:
        confidence = min(1.0, text_coverage_ratio * 2 + 0.5)
    else:
        confidence = min(0.49, native_text_length / settings.low_text_threshold_chars * 0.49)

    return PageHeuristics(
        page_number=page_number,
        native_text_length=native_text_length,
        text_block_count=text_block_count,
        has_large_rasters=has_large_rasters,
        is_effectively_image_only=is_effectively_image_only,
        text_coverage_ratio=text_coverage_ratio,
        confidence=confidence,
        flags=flags,
    )


def _extract_native_text(fitz_page: object) -> str:  # type: ignore[type-arg]
    raw: str = fitz_page.get_text("text")  # type: ignore[attr-defined]
    lines = raw.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _SLIDE_NUM_RE.match(stripped):
            continue
        if any(pattern.match(stripped) for pattern in _HEADER_FOOTER_RES):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


def _render_page_png(fitz_page: object, dpi: int = 150) -> bytes:  # type: ignore[type-arg]
    """Render a page to a PNG bytes blob at the given DPI."""
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)  # type: ignore[name-defined]
    pix = fitz_page.get_pixmap(matrix=mat, alpha=False)  # type: ignore[attr-defined]
    return pix.tobytes("png")
