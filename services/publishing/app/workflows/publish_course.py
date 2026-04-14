from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

from app.workflows.types import PublishCourseInput


@workflow.defn
class PublishCourseWorkflow:
    """Temporal workflow orchestrating the publishing pipeline."""

    @workflow.run
    async def run(self, input: PublishCourseInput) -> None:
        try:
            assets = await workflow.execute_activity(
                "validate_assets",
                input,
                start_to_close_timeout=timedelta(minutes=5),
            )
            extracted = await workflow.execute_activity(
                "extract_text",
                (input, assets),
                start_to_close_timeout=timedelta(minutes=15),
            )
            chunks = await workflow.execute_activity(
                "chunk_content",
                (input, extracted),
                start_to_close_timeout=timedelta(minutes=10),
            )
            embeddings = await workflow.execute_activity(
                "generate_embeddings",
                chunks,
                start_to_close_timeout=timedelta(minutes=20),
            )
            await workflow.execute_activity(
                "index_qdrant",
                (chunks, embeddings),
                start_to_close_timeout=timedelta(minutes=10),
            )
            await workflow.execute_activity(
                "finalize_version",
                input,
                start_to_close_timeout=timedelta(minutes=5),
            )
        except Exception as exc:
            await workflow.execute_activity(
                "mark_version_failed",
                (input, str(exc)),
                start_to_close_timeout=timedelta(minutes=5),
            )
            raise
