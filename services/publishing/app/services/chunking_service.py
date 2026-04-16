from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from app.services.canonical_builder import CanonicalPageRecord

# Rough token estimate: 1 token ≈ 4 characters (good enough for budget checks)
_CHARS_PER_TOKEN = 4

# Boilerplate detection: lines that appear identically in ≥50% of pages
_BOILERPLATE_THRESHOLD = 0.50


@dataclass(frozen=True)
class ContentChunk:
    """A versioned, provenance-rich chunk ready for embedding and indexing."""

    chunk_hash: str
    version_id: str
    course_id: str
    module_id: str
    asset_id: str
    page_or_slide_number: int
    module_title: str
    asset_title: str
    source_type: str
    chunk_index: int
    text: str
    quality_score: float
    content_sources_used: list[str]
    token_estimate: int
    text_preview: str


@dataclass
class ChunkingStats:
    total_chunks: int = 0
    duplicate_chunks_removed: int = 0
    boilerplate_lines_removed: int = 0


class ChunkingService:
    """
    Token-aware, page-boundary-respecting chunker that attaches provenance metadata.

    Rules:
    - Target: ``chunk_target_tokens`` (default 500 tokens ≈ 2000 chars)
    - Hard cap: ``chunk_max_tokens`` (default 800 tokens ≈ 3200 chars)
    - Overlap: ``chunk_overlap_tokens`` (default 80 tokens ≈ 320 chars) within same page only
    - Slide/page decks: prefer one chunk per page unless the page is unusually dense
    - Duplicate chunks (by hash) are removed
    """

    def __init__(
        self,
        *,
        chunk_target_tokens: int = 500,
        chunk_max_tokens: int = 800,
        chunk_overlap_tokens: int = 80,
    ) -> None:
        self._target_chars = chunk_target_tokens * _CHARS_PER_TOKEN
        self._max_chars = chunk_max_tokens * _CHARS_PER_TOKEN
        self._overlap_chars = chunk_overlap_tokens * _CHARS_PER_TOKEN

    def split_pages(
        self,
        pages: list[CanonicalPageRecord],
        *,
        course_id: str,
    ) -> tuple[list[ContentChunk], ChunkingStats]:
        """
        Convert canonical page records into deduplicated content chunks.

        Returns ``(chunks, stats)``.
        """
        stats = ChunkingStats()
        boilerplate = _detect_boilerplate(pages)

        seen_hashes: set[str] = set()
        chunks: list[ContentChunk] = []
        global_index = 0

        for page in pages:
            text = _strip_boilerplate(page.merged_text(), boilerplate)
            text = text.strip()
            if not text:
                continue

            page_chunks = self._split_text(text)
            for raw_text in page_chunks:
                if not raw_text.strip():
                    continue
                chunk_hash = _chunk_hash(
                    raw_text,
                    version_id=page.version_id,
                    asset_id=page.asset_id,
                    page_num=page.page_or_slide_number,
                )
                if chunk_hash in seen_hashes:
                    stats.duplicate_chunks_removed += 1
                    continue
                seen_hashes.add(chunk_hash)

                token_estimate = max(1, len(raw_text) // _CHARS_PER_TOKEN)
                chunks.append(
                    ContentChunk(
                        chunk_hash=chunk_hash,
                        version_id=page.version_id,
                        course_id=course_id,
                        module_id=page.module_id,
                        asset_id=page.asset_id,
                        page_or_slide_number=page.page_or_slide_number,
                        module_title=page.module_title,
                        asset_title=page.asset_title,
                        source_type=page.source_type,
                        chunk_index=global_index,
                        text=raw_text,
                        quality_score=page.quality_score(),
                        content_sources_used=page.content_sources_used(),
                        token_estimate=token_estimate,
                        text_preview=raw_text[:250],
                    )
                )
                global_index += 1

        stats.total_chunks = len(chunks)
        return chunks, stats

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks respecting target/max token limits with overlap."""
        length = len(text)
        if length <= self._max_chars:
            return [text]

        parts: list[str] = []
        start = 0
        while start < length:
            end = min(length, start + self._target_chars)
            # Try to break on a sentence or paragraph boundary within the window
            if end < length:
                end = _find_break(text, start, end)
            part = text[start:end].strip()
            if part:
                parts.append(part)
            if end >= length:
                break
            start = max(start + 1, end - self._overlap_chars)
        return parts


# ── Helpers ──────────────────────────────────────────────────────────────────


def _chunk_hash(text: str, *, version_id: str, asset_id: str, page_num: int) -> str:
    key = f"{text}||{version_id}||{asset_id}||{page_num}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _find_break(text: str, start: int, preferred_end: int) -> int:
    """
    Look backward from ``preferred_end`` for a paragraph or sentence boundary.
    Returns ``preferred_end`` unchanged if no good boundary is found within 20% of range.
    """
    window = (preferred_end - start) // 5  # 20% search window
    search_start = max(start, preferred_end - window)
    # Prefer paragraph break
    idx = text.rfind("\n\n", search_start, preferred_end)
    if idx != -1:
        return idx + 2
    # Fall back to sentence ending
    for punct in (".", "!", "?"):
        idx = text.rfind(punct + " ", search_start, preferred_end)
        if idx != -1:
            return idx + 2
    return preferred_end


def _detect_boilerplate(pages: list[CanonicalPageRecord]) -> set[str]:
    """
    Identify lines that appear identically in ≥50% of pages — likely boilerplate.
    Only considers short lines (≤120 chars) to avoid false positives.
    """
    if len(pages) < 3:
        return set()
    from collections import Counter

    line_counts: Counter[str] = Counter()
    for page in pages:
        seen_lines: set[str] = set()
        for line in page.merged_text().splitlines():
            normalized = line.strip()
            if normalized and len(normalized) <= 120 and normalized not in seen_lines:
                line_counts[normalized] += 1
                seen_lines.add(normalized)

    threshold = max(2, len(pages) * _BOILERPLATE_THRESHOLD)
    return {line for line, count in line_counts.items() if count >= threshold}


def _strip_boilerplate(text: str, boilerplate: set[str]) -> str:
    if not boilerplate:
        return text
    lines = [line for line in text.splitlines() if line.strip() not in boilerplate]
    return "\n".join(lines)

