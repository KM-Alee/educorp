from __future__ import annotations

from app.services.citation_service import build_citations, invalid_citation_refs


def test_build_citations_filters_invalid_refs():
    chunks = [
        {"chunk_id": "c1", "module_title": "M1", "asset_title": "A1", "text": "alpha"},
        {"chunk_id": "c2", "module_title": "M2", "asset_title": "A2", "text": "beta"},
    ]
    answer = "See [1] and [3]."

    citations = build_citations(answer, chunks)
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == "c1"

    invalid = invalid_citation_refs(answer, len(chunks))
    assert invalid == [3]
