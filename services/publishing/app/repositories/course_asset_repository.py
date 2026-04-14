from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class CourseAssetRecord:
    asset_id: UUID
    module_id: UUID
    asset_type: str
    file_name: str
    storage_path: str
    upload_status: str


class CourseAssetRepository:
    """Read-only access to course assets stored in the course schema."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_assets_for_course(self, course_id: UUID) -> list[CourseAssetRecord]:
        query = text(
            """
            SELECT a.id AS asset_id,
                   a.module_id AS module_id,
                   a.asset_type AS asset_type,
                   a.file_name AS file_name,
                   a.storage_path AS storage_path,
                   a.upload_status AS upload_status
              FROM course.assets a
              JOIN course.modules m ON m.id = a.module_id
             WHERE m.course_id = :course_id
             ORDER BY m.sort_order, a.sort_order
            """
        )
        result = await self._session.execute(query, {"course_id": str(course_id)})
        rows = result.mappings().all()
        return [
            CourseAssetRecord(
                asset_id=row["asset_id"],
                module_id=row["module_id"],
                asset_type=row["asset_type"],
                file_name=row["file_name"],
                storage_path=row["storage_path"],
                upload_status=row["upload_status"],
            )
            for row in rows
        ]
