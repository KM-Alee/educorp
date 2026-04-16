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
from app.services.chunking_service import ChunkingService, ContentChunk
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService
from app.services.qdrant_service import QdrantService, build_qdrant_point
from app.workflows.types import (
    ArtifactActivityInput,
    IndexArtifactsInput,
    QualityReportInput,
    VersionFailureInput,
)
from educorp_common.errors import EduCorpError, NotFoundError, ValidationError

STEP_PREFLIGHT = "preflight_review"
STEP_EXTRACT = "extract_text"
STEP_CHUNK = "chunk_content"
STEP_EMBED = "generate_embeddings"
STEP_INDEX = "index_qdrant"
STEP_QUALITY = "generate_quality_report"
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
            chunk_target_tokens=settings.chunk_target_tokens,
            chunk_max_tokens=settings.chunk_max_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
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
        """
        Run the full staged extraction pipeline for every asset in the manifest.

        Produces a ``CANONICAL_PAGES`` artifact and per-asset MinIO artifacts.
        Returns the canonical pages artifact UUID.
        """
        async with self._session_factory() as session:
            await _mark_step(session, version_id, STEP_EXTRACT, "RUNNING")
            try:
                manifest_repo = VersionManifestRepository(session)
                artifact_repo = VersionArtifactRepository(session)
                version_repo = CourseVersionRepository(session)

                manifest_modules = await manifest_repo.list_modules_for_version(version_id)
                module_titles: dict[str, str] = {
                    str(m.module_id): m.title for m in manifest_modules
                }

                version = await version_repo.get_by_id(version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                assets = await manifest_repo.list_assets_for_version(version_id)
                all_canonical_pages: list[dict[str, object]] = []
                agg_stats: dict[str, int] = {
                    "total_pages": 0,
                    "ocr_pages": 0,
                    "nanogpt_pages": 0,
                    "low_confidence_pages": 0,
                    "total_assets": len(assets),
                }
                budget_warnings: list[str] = []

                for asset in assets:
                    raw_bytes = await self._read_object(asset.storage_path)
                    module_title = module_titles.get(str(asset.module_id), "")

                    records, asset_stats = await self._extractor.extract_canonical_pages(
                        asset_type=asset.asset_type,
                        data=raw_bytes,
                        asset_id=str(asset.asset_id),
                        version_id=str(version_id),
                        module_id=str(asset.module_id),
                        module_title=module_title,
                        asset_title=asset.title,
                    )

                    # Detect per-asset visual enrichment budget overruns
                    max_pages = settings.visual_enrichment_max_pages_per_asset
                    max_pct = settings.visual_enrichment_max_percent_per_asset
                    total = asset_stats["total_pages"]
                    nanogpt = asset_stats["nanogpt_pages"]
                    if total > 0 and (nanogpt > max_pages or nanogpt / total > max_pct):
                        budget_warnings.append(
                            f"Asset {asset.file_name}: {nanogpt}/{total} pages sent to NanoGPT "
                            f"(limit: {max_pages} pages / {int(max_pct * 100)}%)"
                        )

                    # Save per-asset canonical pages to MinIO for auditability
                    await self._artifact_storage.put_json(
                        f"versions/{version_id}/extraction/pages/{asset.asset_id}/canonical.json",
                        [r.to_dict() for r in records],
                    )

                    for key in ("total_pages", "ocr_pages", "nanogpt_pages", "low_confidence_pages"):
                        agg_stats[key] = agg_stats[key] + asset_stats.get(key, 0)

                    all_canonical_pages.extend(r.to_dict() for r in records)

                # Gate: if budget was exceeded, return to REVIEW_REQUIRED
                if budget_warnings:
                    version.status = "REVIEW_REQUIRED"
                    existing_summary = version.preflight_summary_json or {}
                    version.preflight_summary_json = {
                        **existing_summary,
                        "budget_warnings": budget_warnings,
                    }
                    await version_repo.update(version)
                    await _mark_step(
                        session,
                        version_id,
                        STEP_EXTRACT,
                        "FAILED",
                        error_message="Visual enrichment budget exceeded; operator review required",
                    )
                    await session.commit()
                    raise EduCorpError(
                        code="BUDGET_EXCEEDED",
                        message="Visual enrichment budget exceeded",
                        status_code=400,
                    )

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=version_id,
                    artifact_type="CANONICAL_PAGES",
                    object_path=f"versions/{version_id}/extraction/canonical_pages.json",
                    payload=all_canonical_pages,
                    metadata=agg_stats,
                )

                await _mark_step(
                    session, version_id, STEP_EXTRACT, "COMPLETED", metadata=agg_stats
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session, version_id, STEP_EXTRACT, "FAILED", error_message=str(exc)
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_CHUNK)
    async def chunk_content(self, payload: ArtifactActivityInput) -> UUID:
        """
        Load canonical pages and produce provenance-rich chunks.
        Persists chunk references to the DB and saves chunks.json to MinIO.
        """
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_CHUNK, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                version_repo = CourseVersionRepository(session)
                chunk_repo = ChunkRepository(session)

                canon_artifact = await artifact_repo.get_by_id(payload.artifact_id)
                if canon_artifact is None:
                    raise NotFoundError("Canonical pages artifact not found")

                version = await version_repo.get_by_id(payload.version_id)
                if version is None:
                    raise NotFoundError("Publishing version not found")

                raw_pages = await self._artifact_storage.get_json(canon_artifact.object_path)
                canon_pages = [_dict_to_canonical(p) for p in raw_pages]

                await chunk_repo.delete_for_version(payload.version_id)

                chunks, chunk_stats = self._chunker.split_pages(
                    canon_pages, course_id=str(version.course_id)
                )

                chunk_records = [_chunk_to_dict(c) for c in chunks]

                db_chunks = [
                    Chunk(
                        id=uuid5(
                            payload.version_id,
                            f"{c.asset_id}:{c.page_or_slide_number}:{c.chunk_index}",
                        ),
                        version_id=payload.version_id,
                        course_id=version.course_id,
                        module_id=UUID(c.module_id),
                        asset_id=UUID(c.asset_id),
                        chunk_index=c.chunk_index,
                        char_start=None,
                        char_end=None,
                        token_count=c.token_estimate,
                        text_preview=c.text_preview,
                    )
                    for c in chunks
                ]
                await chunk_repo.create_many(db_chunks)
                version.total_chunks = len(chunk_records)
                await version_repo.update(version)

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=payload.version_id,
                    artifact_type="CHUNKS",
                    object_path=f"versions/{payload.version_id}/chunks/chunks.json",
                    payload=chunk_records,
                    metadata={
                        "total_chunks": chunk_stats.total_chunks,
                        "duplicate_chunks_removed": chunk_stats.duplicate_chunks_removed,
                    },
                )

                await _mark_step(
                    session, payload.version_id, STEP_CHUNK, "COMPLETED",
                    metadata={
                        "total_chunks": chunk_stats.total_chunks,
                        "duplicate_chunks_removed": chunk_stats.duplicate_chunks_removed,
                    },
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session, payload.version_id, STEP_CHUNK, "FAILED", error_message=str(exc)
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_EMBED)
    async def generate_embeddings(self, payload: ArtifactActivityInput) -> UUID:
        """Load chunks and generate embeddings with Redis caching."""
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_EMBED, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                chunk_artifact = await artifact_repo.get_by_id(payload.artifact_id)
                if chunk_artifact is None:
                    raise NotFoundError("Chunks artifact not found")

                chunk_records: list[dict[str, object]] = await self._artifact_storage.get_json(
                    chunk_artifact.object_path
                )
                texts = [str(c["text"]) for c in chunk_records]
                hashes = [str(c["chunk_hash"]) for c in chunk_records]

                vectors, reused, created = await EmbeddingService().embed_texts(
                    texts, chunk_hashes=hashes
                )

                if len(vectors) != len(chunk_records):
                    raise EduCorpError(
                        code="AI_PROVIDER_ERROR",
                        message="Embedding count does not match chunk count",
                        status_code=502,
                    )

                embedding_records = [
                    {"chunk_hash": chunk["chunk_hash"], "vector": vector}
                    for chunk, vector in zip(chunk_records, vectors, strict=False)
                ]

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=payload.version_id,
                    artifact_type="EMBEDDINGS",
                    object_path=f"versions/{payload.version_id}/artifacts/embeddings.json",
                    payload=embedding_records,
                    metadata={
                        "total_embeddings": len(embedding_records),
                        "embeddings_reused": reused,
                        "embeddings_created": created,
                    },
                )

                await _mark_step(
                    session, payload.version_id, STEP_EMBED, "COMPLETED",
                    metadata={
                        "total_embeddings": len(embedding_records),
                        "embeddings_reused": reused,
                        "embeddings_created": created,
                    },
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session, payload.version_id, STEP_EMBED, "FAILED", error_message=str(exc)
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_INDEX)
    async def index_qdrant(self, payload: IndexArtifactsInput) -> None:
        """Version-safe Qdrant upsert with full payload fields."""
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_INDEX, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)
                chunks_artifact = await artifact_repo.get_by_id(payload.chunks_artifact_id)
                embeddings_artifact = await artifact_repo.get_by_id(
                    payload.embeddings_artifact_id
                )
                if chunks_artifact is None or embeddings_artifact is None:
                    raise NotFoundError("Publishing artifacts not found")

                chunk_records: list[dict[str, object]] = await self._artifact_storage.get_json(
                    chunks_artifact.object_path
                )
                embedding_records: list[dict[str, object]] = await self._artifact_storage.get_json(
                    embeddings_artifact.object_path
                )

                # Build embedding lookup by chunk_hash for safe pairing
                embed_by_hash: dict[str, list[float]] = {
                    str(e["chunk_hash"]): e["vector"]  # type: ignore[assignment]
                    for e in embedding_records
                }

                points = [
                    build_qdrant_point(chunk, embed_by_hash[str(chunk["chunk_hash"])])
                    for chunk in chunk_records
                    if str(chunk["chunk_hash"]) in embed_by_hash
                ]

                qdrant = QdrantService()
                qdrant.upsert_version_safe(str(payload.version_id), points)

                await _mark_step(
                    session, payload.version_id, STEP_INDEX, "COMPLETED",
                    metadata={"total_points": len(points)},
                )
                await session.commit()
            except Exception as exc:
                await _mark_step(
                    session, payload.version_id, STEP_INDEX, "FAILED", error_message=str(exc)
                )
                await session.commit()
                raise

    @activity.defn(name=STEP_QUALITY)
    async def generate_quality_report(self, payload: QualityReportInput) -> UUID:
        """Aggregate stats from extraction, chunking, and embedding into a quality report."""
        async with self._session_factory() as session:
            await _mark_step(session, payload.version_id, STEP_QUALITY, "RUNNING")
            try:
                artifact_repo = VersionArtifactRepository(session)

                ext_a = await artifact_repo.get_by_id(payload.extraction_artifact_id)
                chk_a = await artifact_repo.get_by_id(payload.chunks_artifact_id)
                emb_a = await artifact_repo.get_by_id(payload.embeddings_artifact_id)

                ext_meta = (ext_a.artifact_metadata or {}) if ext_a else {}
                chk_meta = (chk_a.artifact_metadata or {}) if chk_a else {}
                emb_meta = (emb_a.artifact_metadata or {}) if emb_a else {}

                report: dict[str, object] = {
                    "version_id": str(payload.version_id),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_assets": ext_meta.get("total_assets", 0),
                    "total_pages": ext_meta.get("total_pages", 0),
                    "ocr_pages_count": ext_meta.get("ocr_pages", 0),
                    "nanogpt_pages_count": ext_meta.get("nanogpt_pages", 0),
                    "low_confidence_pages_count": ext_meta.get("low_confidence_pages", 0),
                    "total_chunks": chk_meta.get("total_chunks", 0),
                    "duplicate_chunks_removed": chk_meta.get("duplicate_chunks_removed", 0),
                    "total_embeddings": emb_meta.get("total_embeddings", 0),
                    "total_embeddings_reused": emb_meta.get("embeddings_reused", 0),
                    "total_embeddings_created": emb_meta.get("embeddings_created", 0),
                    "visual_enrichment_enabled": settings.visual_enrichment_enabled,
                    "visual_enrichment_max_pages_per_asset": settings.visual_enrichment_max_pages_per_asset,
                    "ocr_confidence_threshold": settings.ocr_confidence_threshold,
                    "visual_confidence_threshold": settings.visual_confidence_threshold,
                    "low_text_threshold_chars": settings.low_text_threshold_chars,
                    "embedding_model": settings.embedding_model,
                }

                artifact = await _store_artifact(
                    session=session,
                    artifact_storage=self._artifact_storage,
                    artifact_repo=artifact_repo,
                    version_id=payload.version_id,
                    artifact_type="QUALITY_REPORT",
                    object_path=f"versions/{payload.version_id}/reports/quality-report.json",
                    payload=report,
                    metadata={"kind": "quality_report"},
                )

                await _mark_step(
                    session, payload.version_id, STEP_QUALITY, "COMPLETED",
                    metadata={"quality_report_artifact_id": str(artifact.id)},
                )
                await session.commit()
                return artifact.id
            except Exception as exc:
                await _mark_step(
                    session, payload.version_id, STEP_QUALITY, "FAILED", error_message=str(exc)
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


# ── Module-level helpers ──────────────────────────────────────────────────────


def _dict_to_canonical(d: dict[str, object]):  # type: ignore[return]
    """Reconstruct a CanonicalPageRecord from its stored dict representation."""
    from app.services.canonical_builder import build_canonical_page

    return build_canonical_page(
        version_id=str(d.get("version_id", "")),
        asset_id=str(d.get("asset_id", "")),
        source_type=str(d.get("source_type", "")),
        page_or_slide_number=int(d.get("page_or_slide_number", 1)),
        module_id=str(d.get("module_id", "")),
        module_title=str(d.get("module_title", "")),
        asset_title=str(d.get("asset_title", "")),
        native_text=str(d.get("native_text", "")),
        ocr_text=str(d.get("ocr_text", "")),
        visual_summary=str(d.get("visual_summary", "")),
        has_visual_summary=bool(d.get("has_visual_summary", False)),
        text_confidence=float(d.get("text_confidence", 1.0)),
        visual_confidence=float(d.get("visual_confidence", 0.0)),
        flags=list(d.get("flags", [])),
    )


def _chunk_to_dict(c: ContentChunk) -> dict[str, object]:
    return {
        "chunk_hash": c.chunk_hash,
        "version_id": c.version_id,
        "course_id": c.course_id,
        "module_id": c.module_id,
        "asset_id": c.asset_id,
        "page_or_slide_number": c.page_or_slide_number,
        "module_title": c.module_title,
        "asset_title": c.asset_title,
        "source_type": c.source_type,
        "chunk_index": c.chunk_index,
        "text": c.text,
        "quality_score": c.quality_score,
        "content_sources_used": c.content_sources_used,
        "token_estimate": c.token_estimate,
        "text_preview": c.text_preview,
    }


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
