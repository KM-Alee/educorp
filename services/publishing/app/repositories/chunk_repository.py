from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk


class ChunkRepository:
    """Data access for chunk references."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, chunks: list[Chunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def delete_for_version(self, version_id) -> None:
        await self._session.execute(
            delete(Chunk).where(Chunk.version_id == version_id)
        )
        await self._session.flush()
