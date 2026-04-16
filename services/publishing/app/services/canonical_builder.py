from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


@dataclass
class CanonicalPageRecord:
    """
    Immutable per-page/slide record created before chunking.

    ``content_hash`` is derived from the merged text after normalization.
    """

    version_id: str
    asset_id: str
    source_type: str
    page_or_slide_number: int
    module_id: str
    module_title: str
    asset_title: str
    native_text: str
    ocr_text: str
    visual_summary: str
    has_visual_summary: bool
    text_confidence: float
    visual_confidence: float
    content_hash: str
    flags: list[str] = field(default_factory=list)

    def merged_text(self) -> str:
        """Return the best available text for this page."""
        parts: list[str] = []
        if self.native_text.strip():
            parts.append(self.native_text.strip())
        if self.ocr_text.strip() and self.ocr_text.strip() != self.native_text.strip():
            parts.append(self.ocr_text.strip())
        if self.visual_summary.strip():
            parts.append(self.visual_summary.strip())
        return "\n".join(parts)

    def content_sources_used(self) -> list[str]:
        sources: list[str] = []
        if self.native_text.strip():
            sources.append("native_text")
        if self.ocr_text.strip():
            sources.append("ocr_text")
        if self.visual_summary.strip():
            sources.append("visual_summary")
        return sources or ["native_text"]

    def quality_score(self) -> float:
        """Composite quality score (0.0–1.0) for downstream ranking."""
        base = self.text_confidence
        if self.has_visual_summary:
            base = max(base, self.visual_confidence)
        # Penalise pages with no usable text at all
        if not self.merged_text().strip():
            return 0.0
        return round(min(1.0, base), 4)

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["merged_text"] = self.merged_text()
        d["content_sources_used"] = self.content_sources_used()
        d["quality_score"] = self.quality_score()
        return d


def compute_content_hash(text: str) -> str:
    """SHA-256 of NFC-normalized, whitespace-collapsed, lower-cased text."""
    import unicodedata

    normalized = unicodedata.normalize("NFC", text.lower())
    collapsed = " ".join(normalized.split())
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


def build_canonical_page(
    *,
    version_id: str,
    asset_id: str,
    source_type: str,
    page_or_slide_number: int,
    module_id: str,
    module_title: str,
    asset_title: str,
    native_text: str,
    ocr_text: str = "",
    visual_summary: str = "",
    has_visual_summary: bool = False,
    text_confidence: float = 1.0,
    visual_confidence: float = 0.0,
    flags: list[str] | None = None,
) -> CanonicalPageRecord:
    merged = "\n".join(
        t
        for t in [native_text.strip(), ocr_text.strip(), visual_summary.strip()]
        if t
    )
    content_hash = compute_content_hash(merged)
    return CanonicalPageRecord(
        version_id=version_id,
        asset_id=asset_id,
        source_type=source_type,
        page_or_slide_number=page_or_slide_number,
        module_id=module_id,
        module_title=module_title,
        asset_title=asset_title,
        native_text=native_text,
        ocr_text=ocr_text,
        visual_summary=visual_summary,
        has_visual_summary=has_visual_summary,
        text_confidence=text_confidence,
        visual_confidence=visual_confidence,
        content_hash=content_hash,
        flags=flags or [],
    )
