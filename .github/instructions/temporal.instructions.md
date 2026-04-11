---
applyTo: "services/publishing/app/**/*.py,services/*/app/**/workflows/**,services/*/app/**/activities/**"
---

# Temporal Workflow Conventions

## Workflow Definition
```python
@workflow.defn
class PublishCourseWorkflow:
    @workflow.run
    async def run(self, input: PublishInput) -> PublishResult:
        # Execute activities in sequence
        validation = await workflow.execute_activity(
            validate_assets,
            input.version_id,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        # ... more activities
```

## Activity Definition
```python
@activity.defn
async def extract_text(version_id: str) -> ExtractResult:
    # Activities contain the actual I/O logic
    # They can be retried independently by Temporal
    ...
```

## Conventions
- Workflows are pure orchestration — no I/O or side effects
- Activities contain all I/O (DB, API calls, file processing)
- Each activity should be independently retryable and idempotent
- Use heartbeats for long-running activities (embedding generation, text extraction)
- Set appropriate timeouts:
  - `start_to_close_timeout`: max time for single attempt
  - `schedule_to_close_timeout`: max time including retries
  - `heartbeat_timeout`: for long activities with heartbeats

## Publishing Workflow Steps
1. `ValidateAssetsActivity` — Verify all assets exist in MinIO
2. `ExtractTextActivity` — Download and extract text from each asset
3. `ChunkContentActivity` — Split extracted text into chunks with metadata
4. `GenerateEmbeddingsActivity` — Call embedding API in batches
5. `IndexInQdrantActivity` — Upsert vectors to Qdrant collection
6. `FinalizeVersionActivity` — Mark version READY, update course, emit event

## Error Handling
- Activities that fail after all retries cause the workflow to fail
- Workflow failure sets version status to FAILED with error details
- Admin can retry failed workflows via API → Temporal handles re-execution
- Use `workflow.execute_activity` return values to pass data between steps

## Worker Configuration
```python
worker = Worker(
    client=temporal_client,
    task_queue="publishing-tasks",
    workflows=[PublishCourseWorkflow],
    activities=[validate_assets, extract_text, chunk_content, ...],
)
```

## Testing
- Test workflows with `temporalio.testing.WorkflowEnvironment`
- Mock activities for unit testing workflow logic
- Integration test: run workflow against real Temporal with mocked extractors/LLM
