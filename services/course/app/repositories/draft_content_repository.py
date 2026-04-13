from __future__ import annotations

from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase


class DraftContentRepository:
    """MongoDB data access for rich draft content."""

    COLLECTION = "course_drafts"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db[self.COLLECTION]

    async def upsert(self, course_id: UUID, content: dict[str, Any]) -> None:
        await self._collection.update_one(
            {"course_id": str(course_id)},
            {"$set": {"course_id": str(course_id), **content}},
            upsert=True,
        )

    async def get(self, course_id: UUID) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"course_id": str(course_id)})
        if doc:
            doc.pop("_id", None)
        return doc

    async def delete(self, course_id: UUID) -> None:
        await self._collection.delete_one({"course_id": str(course_id)})
