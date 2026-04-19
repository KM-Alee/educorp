from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class AiJobsRepository:
    """Mongo-backed repository for AI instructor jobs."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db["ai_jobs"]

    async def create_job(self, job: dict[str, Any]) -> None:
        job.setdefault("created_at", datetime.now(timezone.utc))
        await self._collection.insert_one(job)

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"job_id": job_id}, {"_id": 0})

    async def update_job(self, job_id: str, updates: dict[str, Any]) -> None:
        await self._collection.update_one({"job_id": job_id}, {"$set": updates})

    async def list_jobs(
        self,
        *,
        filters: dict[str, Any],
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        total = await self._collection.count_documents(filters)
        cursor = (
            self._collection.find(filters, {"_id": 0})
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return await cursor.to_list(length=page_size), total
