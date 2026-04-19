from __future__ import annotations

import re


def build_citations(answer: str, chunks: list[dict]) -> list[dict]:
    citations: list[dict] = []
    referenced = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))

    for i, chunk in enumerate(chunks):
        idx = i + 1
        if idx in referenced:
            citations.append(
                {
                    "chunk_id": chunk.get("chunk_id", str(idx)),
                    "module_title": chunk.get("module_title"),
                    "asset_title": chunk.get("asset_title"),
                    "text_snippet": str(chunk.get("text", ""))[:200],
                    "page_number": chunk.get("page_number"),
                }
            )

    return citations


def invalid_citation_refs(answer: str, chunk_count: int) -> list[int]:
    referenced = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
    return [r for r in referenced if r < 1 or r > chunk_count]
