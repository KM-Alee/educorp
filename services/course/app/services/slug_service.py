from __future__ import annotations

import re
import unicodedata

from app.repositories.course_repository import CourseRepository


class SlugService:
    """Deterministic slug generation with collision resolution."""

    def __init__(self, course_repo: CourseRepository) -> None:
        self._repo = course_repo

    async def generate(self, title: str, *, exclude_id=None) -> str:
        base = self._slugify(title)
        if not base:
            base = "course"

        candidate = base
        suffix = 2
        while await self._repo.slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _slugify(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text.strip("-")
