from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    char_start: int | None
    char_end: int | None
    token_count: int | None


class ChunkingService:
    """Simple character-based chunking with overlap."""

    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = max(1, chunk_size)
        self._chunk_overlap = max(0, min(chunk_overlap, self._chunk_size - 1))

    def split(self, text: str) -> list[TextChunk]:
        stripped = text.strip()
        if not stripped:
            return []

        chunks: list[TextChunk] = []
        start = 0
        idx = 0
        length = len(stripped)

        while start < length:
            end = min(length, start + self._chunk_size)
            chunk_text = stripped[start:end]
            token_count = len(chunk_text.split())
            chunks.append(
                TextChunk(
                    index=idx,
                    text=chunk_text,
                    char_start=start,
                    char_end=end,
                    token_count=token_count,
                )
            )
            if end >= length:
                break
            start = max(0, end - self._chunk_overlap)
            idx += 1

        return chunks
