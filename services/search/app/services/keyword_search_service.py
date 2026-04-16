from __future__ import annotations

from app.repositories.course_search_repository import CourseSearchRepository
from app.schemas.search import CourseSearchItem


class KeywordSearchService:
    """Keyword search over PUBLISHED, activated course catalog using PostgreSQL FTS."""

    def __init__(self, repo: CourseSearchRepository) -> None:
        self._repo = repo

    async def search(
        self,
        *,
        query: str | None,
        category: str | None,
        difficulty: str | None,
        tags: list[str] | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CourseSearchItem], int]:
        rows, total = await self._repo.search_courses(
            query=query,
            category=category,
            difficulty=difficulty,
            tags=tags,
            page=page,
            page_size=page_size,
        )
        items: list[CourseSearchItem] = []
        for row in rows:
            ts_rank = float(row.get("ts_rank", 1.0))
            matched_in = _matched_fields(query or "", row, ts_rank)
            items.append(
                CourseSearchItem(
                    course_id=row["id"],
                    title=row["title"],
                    short_description=row.get("short_description"),
                    category=row.get("category"),
                    difficulty=row.get("difficulty"),
                    relevance_score=_score(ts_rank, matched_in),
                    matched_in=matched_in,
                )
            )
        return items, total


def _matched_fields(query: str, row: dict, ts_rank: float) -> list[str]:
    if not query:
        return []
    q = query.lower()
    matched: list[str] = []
    title = (row.get("title") or "").lower()
    description = (row.get("short_description") or "").lower()
    tags_val = row.get("tags") or []
    if q in title:
        matched.append("title")
    if q in description:
        matched.append("short_description")
    if any(q in (t or "").lower() for t in tags_val):
        matched.append("tags")
    # If FTS matched but we didn't find a substring match above, record it
    if ts_rank > 0 and not matched:
        matched.append("content")
    return matched


def _score(ts_rank: float, matched_in: list[str]) -> float:
    """Convert FTS ts_rank into a 0–1 relevance score."""
    if not matched_in:
        return 0.5
    if ts_rank > 0:
        # ts_rank_cd is in [0, 1]; scale up so typical matches look good
        return min(0.99, 0.5 + ts_rank * 5)
    if "title" in matched_in:
        return 0.9
    return 0.7
