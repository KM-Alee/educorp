from __future__ import annotations

import math
import re
from collections import Counter
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.services.embedding_client import EmbeddingClient


class QdrantRetriever:
    """Retrieve course chunks from Qdrant for AI answers."""

    def __init__(self, qdrant: QdrantClient, embedding_client: EmbeddingClient) -> None:
        self._qdrant = qdrant
        self._embedding = embedding_client
        self._collection = settings.qdrant_collection

    async def retrieve(
        self,
        *,
        course_id: UUID,
        version_id: UUID,
        question: str,
        module_id: UUID | None,
        asset_id: UUID | None = None,
        score_threshold: float | None = None,
    ) -> tuple[list[dict], list[float]]:
        """Retrieve chunks from Qdrant.

        ``score_threshold`` overrides the default ``settings.relevance_threshold``.
        Pass ``0.0`` to fetch all content regardless of similarity (e.g. for
        instructor-tool jobs that need the full course context).
        """
        must = [
            qmodels.FieldCondition(
                key="course_id",
                match=qmodels.MatchValue(value=str(course_id)),
            ),
            qmodels.FieldCondition(
                key="version_id",
                match=qmodels.MatchValue(value=str(version_id)),
            ),
        ]
        if module_id:
            must.append(
                qmodels.FieldCondition(
                    key="module_id",
                    match=qmodels.MatchValue(value=str(module_id)),
                )
            )
        if asset_id:
            must.append(
                qmodels.FieldCondition(
                    key="asset_id",
                    match=qmodels.MatchValue(value=str(asset_id)),
                )
            )

        query_filter = qmodels.Filter(must=must)

        # Asset-scoped retrieval should return the full indexed file so the model
        # sees the entire selected document instead of a similarity-trimmed subset.
        if asset_id is not None:
            points = self._scroll_points(query_filter=query_filter, limit=settings.retrieval_full_scan_limit)
            ordered_points = sorted(points, key=_point_sort_key)
            chunks = [self._point_to_chunk(item) for item in ordered_points]
            return chunks, [1.0] * len(chunks)

        # score_threshold=0.0 is used by instructor tools to request the full
        # available context, not just the top vector matches.
        if score_threshold == 0.0:
            points = self._scroll_points(query_filter=query_filter, limit=settings.retrieval_full_scan_limit)
            ordered_points = sorted(points, key=_point_sort_key)
            chunks = [self._point_to_chunk(item) for item in ordered_points]
            return chunks, [1.0] * len(chunks)

        vector = await self._embedding.embed_query(question)
        dense_results = self._qdrant.query_points(
            collection_name=self._collection,
            query=vector,
            limit=max(settings.retrieval_top_k * 3, settings.retrieval_candidate_pool // 2),
            query_filter=query_filter,
            with_payload=True,
        ).points

        lexical_candidates = self._scroll_points(
            query_filter=query_filter,
            limit=settings.retrieval_candidate_pool,
        )

        combined = _combine_hybrid_results(dense_results, lexical_candidates, question)
        threshold = score_threshold if score_threshold is not None else settings.relevance_threshold

        ranked = [item for item in combined if item[1] >= threshold]
        if not ranked:
            ranked = combined[: settings.retrieval_top_k]

        chunks = [self._point_to_chunk(item) for item, _ in ranked[: settings.retrieval_top_k]]
        scores = [score for _, score in ranked[: settings.retrieval_top_k]]
        return chunks, scores

    def _scroll_points(
        self,
        *,
        query_filter: qmodels.Filter,
        limit: int,
    ) -> list:
        points: list = []
        offset = None

        while len(points) < limit:
            batch_size = min(128, limit - len(points))
            batch, offset = self._qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=query_filter,
                with_payload=True,
                with_vectors=False,
                limit=batch_size,
                offset=offset,
            )
            if not batch:
                break
            points.extend(batch)
            if offset is None:
                break

        return points

    def _point_to_chunk(self, item) -> dict:
        payload = item.payload or {}
        return {
            "chunk_id": str(item.id),
            "course_id": payload.get("course_id"),
            "version_id": payload.get("version_id"),
            "module_id": payload.get("module_id"),
            "module_title": payload.get("module_title"),
            "asset_id": payload.get("asset_id"),
            "asset_title": payload.get("asset_title"),
            "text": payload.get("text", ""),
            "chunk_index": payload.get("chunk_index", 0),
            "page_number": payload.get("page_or_slide_number"),
            "section_title": payload.get("section_title"),
        }


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _point_sort_key(point) -> tuple[int, int, str]:
    payload = point.payload or {}
    page = int(payload.get("page_or_slide_number") or 0)
    chunk_index = int(payload.get("chunk_index") or 0)
    return (page, chunk_index, str(point.id))


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def _combine_hybrid_results(dense_results: list, lexical_candidates: list, question: str) -> list[tuple[object, float]]:
    question_tokens = _tokenize(question)
    lexical_scores = _bm25_scores(lexical_candidates, question_tokens)

    point_by_id: dict[str, object] = {}
    dense_scores: dict[str, float] = {}

    for point in lexical_candidates:
        point_by_id[str(point.id)] = point
    for point in dense_results:
        point_id = str(point.id)
        point_by_id[point_id] = point
        dense_scores[point_id] = float(point.score or 0.0)

    ranked: list[tuple[object, float]] = []
    for point_id, point in point_by_id.items():
        dense_component = max(0.0, min(1.0, dense_scores.get(point_id, 0.0)))
        lexical_component = _normalize_bm25(lexical_scores.get(point_id, 0.0))
        hybrid_score = (dense_component * 0.65) + (lexical_component * 0.35)
        ranked.append((point, hybrid_score))

    ranked.sort(key=lambda item: (item[1],) + tuple(-value for value in _point_sort_key(item[0])[:2]), reverse=True)
    return ranked


def _bm25_scores(points: list, question_tokens: list[str]) -> dict[str, float]:
    if not points or not question_tokens:
        return {}

    doc_tokens: dict[str, list[str]] = {}
    doc_freq: Counter[str] = Counter()
    total_length = 0

    for point in points:
        point_id = str(point.id)
        payload = point.payload or {}
        tokens = _tokenize(str(payload.get("text", "")))
        doc_tokens[point_id] = tokens
        total_length += len(tokens)
        for token in set(tokens):
            doc_freq[token] += 1

    if not doc_tokens:
        return {}

    avg_doc_length = max(total_length / len(doc_tokens), 1.0)
    k1 = 1.5
    b = 0.75
    scores: dict[str, float] = {}

    for point_id, tokens in doc_tokens.items():
        if not tokens:
            continue
        token_counts = Counter(tokens)
        doc_length = len(tokens)
        score = 0.0
        for token in question_tokens:
            freq = token_counts.get(token, 0)
            if freq == 0:
                continue
            df = doc_freq.get(token, 0)
            idf = math.log(1 + ((len(doc_tokens) - df + 0.5) / (df + 0.5)))
            numerator = freq * (k1 + 1)
            denominator = freq + (k1 * (1 - b + (b * doc_length / avg_doc_length)))
            score += idf * (numerator / denominator)
        if score > 0:
            scores[point_id] = score

    return scores


def _normalize_bm25(score: float) -> float:
    if score <= 0:
        return 0.0
    return score / (score + 4.0)
