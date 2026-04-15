from __future__ import annotations

import io
from datetime import datetime, timezone
from uuid import UUID, uuid5

import pdfplumber
from miniopy_async import Minio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from app.config import settings
from app.models.chunk import Chunk
from app.models.version_artifact import VersionArtifact
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.course_version_repository import CourseVersionRepository
from app.repositories.publishing_step_repository import PublishingStepRepository
from app.repositories.version_artifact_repository import VersionArtifactRepository
from app.repositories.version_manifest_repository import VersionManifestRepository
from app.services.artifact_storage_service import ArtifactStorageService, read_object
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService
from app.services.qdrant_service import QdrantService
from app.workflows.types import ArtifactActivityInput, IndexArtifactsInput, VersionFailureInput
from educorp_common.errors import EduCorpError, NotFoundError, ValidationError

STEP_PREFLIGHT = "preflight_review"
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
        self._artifact_storage = ArtifactStorageService(minio_client)
        self._extractor = ExtractionService()
        self._chunker = ChunkingService(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    @activity.defn(name=STEP_PREFLIGHT)
    async def preflight_review(self, version_id: UUID) -> UUID:
        async with self._session_factory() as session:
            await _mark_step(session, version_id, STEP_PREFLIGHT, "RUNNING")
            try:
                manifest_repo = VersionManifestRepository(session)
                artifact_repo = VersionArtifactRepository(session)
                version_repo = CourseVersionRepository(session)

                assets = await manifest_repo.list_assets_for_version(version_id)
                if not assets:
                    raise ValidationError("No assets found in manifest")

                flagged_assets: list[dict[str, object]] = []
                review_assets: list[dict[str, object]] = []
                total_pages = 0

                for asset in assets:
                    await self._minio.stat_object(settings.minio_bucket, asset.storage_path)
                    page_estimate = asset.page_estimate
                    image_heavy = False
                    if asset.asset_type == "pdf":
                        raw_bytes = await self._read_object(asset.storage_path)
                        page_estimate, image_heavy = _inspect_pdf(raw_bytes)
                    elif page_estimate is None:
                        page_estimate = 1

                    asset.page_estimate = page_estimate
                    total_pages += page_estimate or 0
                    if image_heavy:
                        flagged_assets.append(
                            {
                                "asset_id": str(asset.asset_id),
                                "file_name": asset.file_name,
                                "reason": "Likely image-heavy PDF",
                            }
                        )
                    review_assets.append(
                        {
                            "asset_id": str(asset.asset_id),
                            "module_id": str(asset.module_id),
                            "file_name": asset.file_name,
                            "asset_type": asset.asset_type,
                            "storage_path": asset.storage_path,
                            "checksum": asset.checksum,
                            "page_estimate": page_estimate,
                            "image_heavy_pdf": image_heavy,
                        }
                    )

                version = await version_repo.get_by_id(version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                summary = {
                    "total_assets": len(review_assets),
                    "flagged_assets": len(flagged_assets),
                    "estimated_pages": total_pages,
                    "image_heavy_assets": len(flagged_assets),
                }

                preflight_payload = {"summary": summary, "assets": review_assets}
                preflight_artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=version_id,
                    artifact_type="PREFLIGHT_REVIEW",
                    object_path=f"versions/{version_id}/review/preflight.json",
                    payload=preflight_payload,
                    metadata={"kind": "review_bundle"},
                )

                await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=version_id,
                    artifact_type="PREFLIGHT_FLAGS",
                    object_path=f"versions/{version_id}/review/flags.json",
                    payload={"flags": flagged_assets},
                    metadata={"kind": "review_flags"},
                )

                version.status = "REVIEW_REQUIRED"
                version.preflight_summary_json = summary
                version.total_assets = len(review_assets)
                await version_repo.update(version)

                await _mark_step(
                    session,
                    version_id,
                    STEP_PREFLIGHT,
                    "COMPLETED",
                    metadata=summary,
                )
                await session.commit()
                return preflight_artifact.id
            except Exception as exc:
                await _mark_step(
                    session,
                    version_id,
                    STEP_PREFLIGHT,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name="mark_version_publishing")
    async def mark_version_publishing(self, version_id: UUID) -> None:
        async with self._session_factory() as session:
            version_repo = CourseVersionRepository(session)
            version = await version_repo.get_by_id(version_id)
            if version is None:
                raise NotFoundError("Publishing version not found")
            version.status = "PUBLISHING"
            version.approval_state = "APPROVED"
            await version_repo.update(version)
            await session.commit()

    @activity.defn(name=STEP_EXTRACT)
    async def extract_text(self, version_id: UUID) -> UUID:
        async with self._session_factory() as session:
            await _mark_step(session, version_id, STEP_EXTRACT, "RUNNING")
            try:
                manifest_repo = VersionManifestRepository(session)
                artifact_repo = VersionArtifactRepository(session)
                version_repo = CourseVersionRepository(session)

                version = await version_repo.get_by_id(version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                assets = await manifest_repo.list_assets_for_version(version_id)
                extracted_records: list[dict[str, object]] = []
                for asset in assets:
                    data = await self._read_object(asset.storage_path)
                    extracted_records.append(
                        {
                            "asset_id": str(asset.asset_id),
                            "module_id": str(asset.module_id),
                            "asset_type": asset.asset_type,
                            "text": self._extractor.extract_text(asset.asset_type, data),
                        }
                    )

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=version_id,
                    artifact_type="EXTRACTED_TEXT",
                    object_path=f"versions/{version_id}/artifacts/extracted.json",
                    payload=extracted_records,
                    metadata={"total_assets": len(extracted_records)},
                )

                await _mark_step(
                    session,
                    version_id,
                    STEP_EXTRACT,
                    "COMPLETED",
                    metadata={"total_assets": len(extracted_records)},
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session,
                    version_id,
                    STEP_EXTRACT,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_CHUNK)
    async def chunk_content(self, payload: ArtifactActivityInput) -> UUID:
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_CHUNK, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                version_repo = CourseVersionRepository(session)
                chunk_repo = ChunkRepository(session)

                extracted_artifact = await artifact_repo.get_by_id(payload.artifact_id)
                if extracted_artifact is None:
                    raise NotFoundError("Publishing artifact not found")

                version = await version_repo.get_by_id(payload.version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                extracted_records = await self._artifact_storage.get_json(
                    extracted_artifact.object_path
                )
                await chunk_repo.delete_for_version(payload.version_id)

                chunk_records: list[dict[str, object]] = []
                db_chunks: list[Chunk] = []
                for asset in extracted_records:
                    asset_id = UUID(str(asset["asset_id"]))
                    module_id = UUID(str(asset["module_id"]))
                    text = str(asset["text"])
                    for chunk in self._chunker.split(text):
                        chunk_id = uuid5(payload.version_id, f"{asset_id}:{chunk.index}")
                        preview = chunk.text[:500] if chunk.text else None
                        chunk_records.append(
                            {
                                "chunk_id": str(chunk_id),
                                "version_id": str(payload.version_id),
                                "course_id": str(version.course_id),
                                "module_id": str(module_id),
                                "asset_id": str(asset_id),
                                "chunk_index": chunk.index,
                                "text": chunk.text,
                                "char_start": chunk.char_start,
                                "char_end": chunk.char_end,
                                "token_count": chunk.token_count,
                                "text_preview": preview,
                            }
                        )
                        db_chunks.append(
                            Chunk(
                                id=chunk_id,
                                version_id=payload.version_id,
                                course_id=version.course_id,
                                module_id=module_id,
                                asset_id=asset_id,
                                chunk_index=chunk.index,
                                char_start=chunk.char_start,
                                char_end=chunk.char_end,
                                token_count=chunk.token_count,
                                text_preview=preview,
                            )
                        )

                await chunk_repo.create_many(db_chunks)
                version.total_chunks = len(chunk_records)
                await version_repo.update(version)

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=payload.version_id,
                    artifact_type="CHUNKS",
                    object_path=f"versions/{payload.version_id}/artifacts/chunks.json",
                    payload=chunk_records,
                    metadata={"total_chunks": len(chunk_records)},
                )

                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_CHUNK,
                    "COMPLETED",
                    metadata={"total_chunks": len(chunk_records)},
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_CHUNK,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_EMBED)
    async def generate_embeddings(self, payload: ArtifactActivityInput) -> UUID:
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_EMBED, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                chunk_artifact = await artifact_repo.get_by_id(payload.artifact_id)
                if chunk_artifact is None:
                    raise NotFoundError("Publishing artifact not found")

                chunk_records = await self._artifact_storage.get_json(chunk_artifact.object_path)
                texts = [str(chunk["text"]) for chunk in chunk_records]
                embeddings = await EmbeddingService().embed_texts(texts)
                embedding_records = [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "vector": vector,
                    }
                    for chunk, vector in zip(chunk_records, embeddings, strict=False)
                ]

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=payload.version_id,
                    artifact_type="EMBEDDINGS",
                    object_path=f"versions/{payload.version_id}/artifacts/embeddings.json",
                    payload=embedding_records,
                    metadata={"total_embeddings": len(embedding_records)},
                )

                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_EMBED,
                    "COMPLETED",
                    metadata={"total_embeddings": len(embedding_records)},
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_EMBED,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_INDEX)
    async def index_qdrant(self, payload: IndexArtifactsInput) -> None:
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_INDEX, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                chunks_artifact = await artifact_repo.get_by_id(payload.chunks_artifact_id)
                embeddings_artifact = await artifact_repo.get_by_id(payload.embeddings_artifact_id)
                if chunks_artifact is None or embeddings_artifact is None:
                    raise NotFoundError("Publishing artifacts not found")

                chunk_records = await self._artifact_storage.get_json(chunks_artifact.object_path)
                embedding_records = await self._artifact_storage.get_json(
                    embeddings_artifact.object_path
                )
                if len(chunk_records) != len(embedding_records):
                    raise EduCorpError(
                        code="AI_PROVIDER_ERROR",
                        message="Embedding count does not match chunk count",
                        status_code=502,
                    )

                qdrant = QdrantService()
                qdrant.ensure_collection()
                points = [
                    _build_point(chunk, embedding["vector"])
                    for chunk, embedding in zip(chunk_records, embedding_records, strict=False)
                ]
                qdrant.upsert(points)

                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_INDEX,
                    "COMPLETED",
                    metadata={"total_points": len(points)},
                )
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session,
                    payload.version_id,
                    STEP_INDEX,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_FINALIZE)
    async def finalize_version(self, version_id: UUID) -> None:
        async with self._session_factory() as session:
            await _mark_step(session, version_id, STEP_FINALIZE, "RUNNING")
            try:
                version_repo = CourseVersionRepository(session)
                version = await version_repo.get_by_id(version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                now = datetime.now(timezone.utc)
                version.status = "READY"
                version.processing_completed_at = now
                version.ready_at = now
                await version_repo.update(version)

                await _mark_step(session, version_id, STEP_FINALIZE, "COMPLETED")
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session,
                    version_id,
                    STEP_FINALIZE,
                    "FAILED",
                    error_message=str(exc),
                )
                await session.commit()
                raise

    @activity.defn(name="mark_version_rejected")
    async def mark_version_rejected(self, version_id: UUID) -> None:
        async with self._session_factory() as session:
            version_repo = CourseVersionRepository(session)
            version = await version_repo.get_by_id(version_id)
            if version is None:
                raise NotFoundError("Publishing version not found")
            version.status = "CANCELLED"
            version.approval_state = "REJECTED"
            version.processing_completed_at = datetime.now(timezone.utc)
            await version_repo.update(version)
            await PublishingStepRepository(session).mark_skipped_for_version(version_id)
            await session.commit()

    @activity.defn(name="mark_version_failed")
    async def mark_version_failed(self, payload: VersionFailureInput) -> None:
        async with self._session_factory() as session:
            version_repo = CourseVersionRepository(session)
            version = await version_repo.get_by_id(payload.version_id)
            if version is None:
                raise NotFoundError("Publishing version not found")
            version.status = "FAILED"
            version.processing_completed_at = datetime.now(timezone.utc)
            version.error_details = {"message": payload.error_message}
            await version_repo.update(version)
            await session.commit()

    async def _read_object(self, object_path: str) -> bytes:
        return await read_object(self._minio, object_path)


def _build_point(chunk: dict[str, object], vector: list[float]):
    from qdrant_client.http import models as qmodels

    payload = {
        "course_id": str(chunk["course_id"]),
        "version_id": str(chunk["version_id"]),
        "module_id": str(chunk["module_id"]),
        "asset_id": str(chunk["asset_id"]),
        "chunk_index": chunk["chunk_index"],
        "text": chunk["text"],
    }
    return qmodels.PointStruct(id=str(chunk["chunk_id"]), vector=vector, payload=payload)


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


async def _store_artifact(
    *,
    session: AsyncSession,
    artifact_storage: ArtifactStorageService,
    artifact_repo: VersionArtifactRepository,
    version_id: UUID,
    artifact_type: str,
    object_path: str,
    payload: object,
    metadata: dict[str, object],
) -> VersionArtifact:
    stored = await artifact_storage.put_json(object_path, payload)
    artifact = VersionArtifact(
        version_id=version_id,
        artifact_type=artifact_type,
        object_path=stored.object_path,
        sha256=stored.sha256,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        artifact_metadata=metadata,
    )
    await artifact_repo.create(artifact)
    session.add(artifact)
    return artifact


def _inspect_pdf(data: bytes) -> tuple[int | None, bool]:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = pdf.pages
            image_heavy = False
            for page in pages:
                text = (page.extract_text() or "").strip()
                if len(text) < 250 and len(page.images) > 0:
                    image_heavy = True
                    break
            return len(pages), image_heavy
    except Exception:
        return None, False
