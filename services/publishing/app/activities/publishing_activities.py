from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid5

from miniopy_async import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from app.config import settings
from app.models.chunk import Chunk
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.course_asset_repository import CourseAssetRepository
from app.repositories.course_version_repository import CourseVersionRepository
from app.repositories.publishing_step_repository import PublishingStepRepository
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService
from app.services.qdrant_service import QdrantService
from app.workflows.types import (
    ChunkPayload,
    CourseAssetInfo,
    ExtractedAsset,
    PublishCourseInput,
)
from educorp_common.errors import EduCorpError, NotFoundError, ValidationError

STEP_VALIDATE = "validate_assets"
STEP_EXTRACT = "extract_text"
STEP_CHUNK = "chunk_content"
STEP_EMBED = "generate_embeddings"
STEP_INDEX = "index_qdrant"
STEP_FINALIZE = "finalize_version"


class PublishingActivities:
    """Temporal activities for the publishing pipeline."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        minio_client: Minio,
    ) -> None:
        self._session_factory = session_factory
        self._minio = minio_client
        self._extractor = ExtractionService()
        self._chunker = ChunkingService(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    @activity.defn(name=STEP_VALIDATE)
    async def validate_assets(self, payload: PublishCourseInput) -> list[CourseAssetInfo]:
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_VALIDATE, "RUNNING")
            try:
                assets = await CourseAssetRepository(session).list_assets_for_course(
                    payload.course_id
                )
                if not assets:
                    raise ValidationError("No assets found for course")

                for asset in assets:
                    if asset.upload_status != "UPLOADED":
                        raise ValidationError("Asset upload is incomplete")
                    await self._minio.stat_object(settings.minio_bucket, asset.storage_path)

                version = await CourseVersionRepository(session).get_by_id(payload.version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")
                version.total_assets = len(assets)
                await CourseVersionRepository(session).update(version)
                await session.commit()

                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_VALIDATE,
                    "COMPLETED",
                    metadata={"total_assets": len(assets)},
                )
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_VALIDATE,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

        return [
            CourseAssetInfo(
                asset_id=asset.asset_id,
                module_id=asset.module_id,
                asset_type=asset.asset_type,
                file_name=asset.file_name,
                storage_path=asset.storage_path,
            )
            for asset in assets
        ]

    @activity.defn(name=STEP_EXTRACT)
    async def extract_text(
        self, payload: tuple[PublishCourseInput, list[CourseAssetInfo]]
    ) -> list[ExtractedAsset]:
        publish_input, assets = payload
        async with self._session_factory() as session:
            await _mark_step(session, publish_input.version_id, STEP_EXTRACT, "RUNNING")
            try:
                extracted: list[ExtractedAsset] = []
                for asset in assets:
                    data = await _read_object(self._minio, asset.storage_path)
                    text = self._extractor.extract_text(asset.asset_type, data)
                    extracted.append(
                        ExtractedAsset(
                            asset_id=asset.asset_id,
                            module_id=asset.module_id,
                            asset_type=asset.asset_type,
                            text=text,
                        )
                    )

                await _mark_step(
                    session,
                    publish_input.version_id,
                    STEP_EXTRACT,
                    "COMPLETED",
                    metadata={"total_assets": len(assets)},
                )
                await session.commit()
                return extracted
            except Exception as exc:
                await _mark_step(
                    session,
                    publish_input.version_id,
                    STEP_EXTRACT,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_CHUNK)
    async def chunk_content(
        self, payload: tuple[PublishCourseInput, list[ExtractedAsset]]
    ) -> list[ChunkPayload]:
        publish_input, extracted_assets = payload
        async with self._session_factory() as session:
            await _mark_step(session, publish_input.version_id, STEP_CHUNK, "RUNNING")
            try:
                chunks: list[ChunkPayload] = []
                chunk_repo = ChunkRepository(session)
                await chunk_repo.delete_for_version(publish_input.version_id)

                for asset in extracted_assets:
                    for chunk in self._chunker.split(asset.text):
                        chunk_id = uuid5(
                            publish_input.version_id,
                            f"{asset.asset_id}:{chunk.index}",
                        )
                        preview = chunk.text[:500] if chunk.text else None
                        chunks.append(
                            ChunkPayload(
                                chunk_id=chunk_id,
                                version_id=publish_input.version_id,
                                course_id=publish_input.course_id,
                                module_id=asset.module_id,
                                asset_id=asset.asset_id,
                                chunk_index=chunk.index,
                                text=chunk.text,
                                char_start=chunk.char_start,
                                char_end=chunk.char_end,
                                token_count=chunk.token_count,
                                text_preview=preview,
                            )
                        )

                await chunk_repo.create_many(
                    [
                        Chunk(
                            id=chunk.chunk_id,
                            version_id=chunk.version_id,
                            course_id=chunk.course_id,
                            module_id=chunk.module_id,
                            asset_id=chunk.asset_id,
                            chunk_index=chunk.chunk_index,
                            char_start=chunk.char_start,
                            char_end=chunk.char_end,
                            token_count=chunk.token_count,
                            text_preview=chunk.text_preview,
                        )
                        for chunk in chunks
                    ]
                )

                version_repo = CourseVersionRepository(session)
                version = await version_repo.get_by_id(publish_input.version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")
                version.total_chunks = len(chunks)
                await version_repo.update(version)

                await _mark_step(
                    session,
                    publish_input.version_id,
                    STEP_CHUNK,
                    "COMPLETED",
                    metadata={"total_chunks": len(chunks)},
                )
                await session.commit()
                return chunks
            except Exception as exc:
                await _mark_step(
                    session,
                    publish_input.version_id,
                    STEP_CHUNK,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_EMBED)
    async def generate_embeddings(self, chunks: list[ChunkPayload]) -> list[list[float]]:
        if not chunks:
            return []

        async with self._session_factory() as session:
            await _mark_step(session, chunks[0].version_id, STEP_EMBED, "RUNNING")
            try:
                texts = [chunk.text for chunk in chunks]
                embeddings = await EmbeddingService().embed_texts(texts)
                await _mark_step(
                    session,
                    chunks[0].version_id,
                    STEP_EMBED,
                    "COMPLETED",
                    metadata={"total_embeddings": len(embeddings)},
                )
                await session.commit()
                return embeddings
            except Exception as exc:
                await _mark_step(
                    session,
                    chunks[0].version_id,
                    STEP_EMBED,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_INDEX)
    async def index_qdrant(
        self, payload: tuple[list[ChunkPayload], list[list[float]]]
    ) -> None:
        chunks, embeddings = payload
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Embedding count does not match chunk count",
                status_code=502,
            )

        async with self._session_factory() as session:
            await _mark_step(session, chunks[0].version_id, STEP_INDEX, "RUNNING")
            try:
                qdrant = QdrantService()
                qdrant.ensure_collection()
                points = []
                for chunk, vector in zip(chunks, embeddings, strict=False):
                    points.append(_build_point(chunk, vector))
                qdrant.upsert(points)

                await _mark_step(
                    session,
                    chunks[0].version_id,
                    STEP_INDEX,
                    "COMPLETED",
                    metadata={"total_points": len(points)},
                )
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session,
                    chunks[0].version_id,
                    STEP_INDEX,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_FINALIZE)
    async def finalize_version(self, payload: PublishCourseInput) -> None:
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_FINALIZE, "RUNNING")
            try:
                version_repo = CourseVersionRepository(session)
                version = await version_repo.get_by_id(payload.version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                now = datetime.now(timezone.utc)
                version.status = "READY"
                version.processing_completed_at = now
                version.ready_at = now
                await version_repo.update(version)

                await session.execute(
                    text(
                        """
                        UPDATE course.courses
                           SET current_version_id = :version_id,
                               visibility = 'PUBLISHED',
                               updated_at = now()
                         WHERE id = :course_id
                        """
                    ),
                    {
                        "version_id": str(payload.version_id),
                        "course_id": str(payload.course_id),
                    },
                )

                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_FINALIZE,
                    "COMPLETED",
                )
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_FINALIZE,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name="mark_version_failed")
    async def mark_version_failed(self, payload: tuple[PublishCourseInput, str]) -> None:
        publish_input, error_message = payload
        async with self._session_factory() as session:
            version_repo = CourseVersionRepository(session)
            version = await version_repo.get_by_id(publish_input.version_id)
            if version is None:
                raise NotFoundError("Publishing version not found")
            version.status = "FAILED"
            version.processing_completed_at = datetime.now(timezone.utc)
            version.error_details = {"message": error_message}
            await version_repo.update(version)
            await session.commit()


def _build_point(chunk: ChunkPayload, vector: list[float]):
    from qdrant_client.http import models as qmodels

    payload = {
        "course_id": str(chunk.course_id),
        "version_id": str(chunk.version_id),
        "module_id": str(chunk.module_id),
        "asset_id": str(chunk.asset_id),
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
    }
    return qmodels.PointStruct(id=str(chunk.chunk_id), vector=vector, payload=payload)


async def _mark_step(
    session: AsyncSession,
    version_id: UUID,
    step_name: str,
    status: str,
    *,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> None:
    repo = PublishingStepRepository(session)
    step = await repo.get_by_version_and_name(version_id, step_name)
    if step is None:
        raise NotFoundError("Publishing step not found")

    now = datetime.now(timezone.utc)
    if status == "RUNNING" and step.started_at is None:
        step.started_at = now
    if status in {"COMPLETED", "FAILED", "SKIPPED"}:
        step.completed_at = now
    step.status = status
    if error_message:
        step.error_message = error_message
    if metadata is not None:
        step.step_metadata = metadata
    await repo.update(step)


async def _read_object(client: Minio, storage_path: str) -> bytes:
    response = await client.get_object(settings.minio_bucket, storage_path)
    data = response.read() if hasattr(response, "read") else response
    if asyncio.iscoroutine(data):
        data = await data
    if hasattr(response, "close"):
        maybe_close = response.close()
        if asyncio.iscoroutine(maybe_close):
            await maybe_close
    return data
