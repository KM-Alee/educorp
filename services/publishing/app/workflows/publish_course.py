from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

from app.workflows.types import (
    ArtifactActivityInput,
    IndexArtifactsInput,
    PublishCourseInput,
    VersionFailureInput,
)


@workflow.defn
class PublishCourseWorkflow:
    """Temporal workflow orchestrating the publishing pipeline."""

    def __init__(self) -> None:
        self._approval: bool | None = None

    @workflow.signal
    async def approve(self) -> None:
        self._approval = True

    @workflow.signal
    async def reject(self) -> None:
        self._approval = False

    @workflow.run
    async def run(self, input: PublishCourseInput) -> None:
        try:
            await workflow.execute_activity(
                "preflight_review",
                input.version_id,
                start_to_close_timeout=timedelta(minutes=5),
            )
            await workflow.wait_condition(lambda: self._approval is not None)

            if not self._approval:
                await workflow.execute_activity(
                    "mark_version_rejected",
                    input.version_id,
                    start_to_close_timeout=timedelta(minutes=5),
                )
                return

            await workflow.execute_activity(
                "mark_version_publishing",
                input.version_id,
                start_to_close_timeout=timedelta(minutes=5),
            )
            extracted_artifact_id = await workflow.execute_activity(
                "extract_text",
                input.version_id,
                start_to_close_timeout=timedelta(minutes=15),
            )
            chunk_artifact_id = await workflow.execute_activity(
                "chunk_content",
                ArtifactActivityInput(
                    version_id=input.version_id,
                    artifact_id=extracted_artifact_id,
                ),
                start_to_close_timeout=timedelta(minutes=10),
            )
            embeddings_artifact_id = await workflow.execute_activity(
                "generate_embeddings",
                ArtifactActivityInput(
                    version_id=input.version_id,
                    artifact_id=chunk_artifact_id,
                ),
                start_to_close_timeout=timedelta(minutes=20),
            )
            await workflow.execute_activity(
                "index_qdrant",
                IndexArtifactsInput(
                    version_id=input.version_id,
                    chunks_artifact_id=chunk_artifact_id,
                    embeddings_artifact_id=embeddings_artifact_id,
                ),
                start_to_close_timeout=timedelta(minutes=10),
            )
            await workflow.execute_activity(
                "finalize_version",
                input.version_id,
                start_to_close_timeout=timedelta(minutes=5),
            )
        except Exception as exc:
            await workflow.execute_activity(
                "mark_version_failed",
                VersionFailureInput(version_id=input.version_id, error_message=str(exc)),
                start_to_close_timeout=timedelta(minutes=5),
            )
            raise
