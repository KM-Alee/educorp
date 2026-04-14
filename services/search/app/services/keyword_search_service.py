from __future__ import annotations

from app.repositories.course_search_repository import CourseSearchRepository
from app.schemas.search import CourseSearchItem


class KeywordSearchService:
    """Keyword search over READY course catalog."""

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
            matched_in = _matched_fields(query or "", row)
            items.append(
                CourseSearchItem(
                    course_id=row["id"],
                    title=row["title"],
                    short_description=row.get("short_description"),
                    category=row.get("category"),
                    difficulty=row.get("difficulty"),
                    relevance_score=_score(matched_in),
                    matched_in=matched_in,
                )
            )
        return items, total


def _matched_fields(query: str, row: dict) -> list[str]:
    if not query:
        return []
    q = query.lower()
    matched: list[str] = []
    title = (row.get("title") or "").lower()
    description = (row.get("description") or "").lower()
    if q in title:
        matched.append("title")
    if q in description:
        matched.append("description")
    return matched


def _score(matched_in: list[str]) -> float:
    if not matched_in:
        return 0.5
    if "title" in matched_in and "description" in matched_in:
        return 0.95
    if "title" in matched_in:
        return 0.9
    return 0.7
