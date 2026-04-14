from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase


class DraftContentRepository:
    """MongoDB data access for rich draft content."""

    COLLECTION = "course_drafts"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db[self.COLLECTION]

    async def upsert(self, course_id: UUID, content: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        await self._collection.update_one(
            {"course_id": str(course_id)},
            {
                "$set": {
                    "course_id": str(course_id),
                    "content": content,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    async def get(self, course_id: UUID) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"course_id": str(course_id)})
        if doc is None:
            return None

        # Support pre-existing flat documents without a migration.
        if "content" not in doc:
            doc = {
                "course_id": doc.get("course_id"),
                "content": {
                    key: value
                    for key, value in doc.items()
                    if key not in {"_id", "course_id", "updated_at"}
                },
                "updated_at": doc.get("updated_at"),
            }

        doc.pop("_id", None)
        return doc

    async def delete(self, course_id: UUID) -> None:
        await self._collection.delete_one({"course_id": str(course_id)})
