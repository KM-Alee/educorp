# EduCorp Runbooks

## Phase 7 Scope

This document is the operational quick reference for the production-readiness slice added in Phase 7.

## Local Operations Checklist

1. Start the full stack with `make up-full`.
2. Seed the platform with `make seed`.
3. Verify learner and AI journeys with `make smoke-phase4` and `make smoke-phase5`.
4. Verify admin ops and observability with `make smoke-phase7`.
5. Open Grafana at `http://localhost:3000` and confirm the provisioned dashboards load.
6. Open Jaeger at `http://localhost:16686` and confirm traces are arriving for `auth-service`, `ai-service`, or another active service.

## Workflow Failures

Symptoms:

- Publishing versions remain in `FAILED`, `REVIEW_REQUIRED`, or `PREPARING`
- Admin workflows page shows repeated retries or error details

Checks:

1. Open Temporal UI at `http://localhost:8088` and inspect the workflow by `workflow_id`.
2. Query `/api/v1/admin/workflows` and `/api/v1/admin/workflows/{workflow_id}`.
3. Review publishing readiness at `/api/v1/publishing/health/ready`.
4. Check Grafana panels for request latency and dependency health.

Recovery:

1. Fix the underlying dependency or content issue.
2. Retry from the admin workflows page or `POST /api/v1/admin/workflows/{workflow_id}/retry`.
3. Re-run `scripts/phase3_dummy_course_publish.py` if a full publish journey needs validation.

## Dead-Letter Growth

Symptoms:

- `EduCorpDeadLetterGrowth` alert fires
- Admin DLQ page shows growing failed messages

Checks:

1. Inspect `/api/v1/admin/dlq` for the failing source, topic, and payload.
2. Review `educorp_domain_events_total{outcome="dead_lettered"}` in Grafana.
3. Check `notification-service` or `analytics-service` logs by correlation ID where available.

Recovery:

1. Patch the consumer or upstream payload issue.
2. Replay individual messages from the admin DLQ page or `POST /api/v1/admin/dlq/{message_id}/replay`.
3. Verify processed-event metrics recover after replay.

## Dependency Degradation

Symptoms:

- Readiness endpoints return `503` or `degraded`
- `educorp_dependency_up` drops to `0`

Checks:

1. Call the affected service `/health/ready` endpoint.
2. Review Grafana dependency panels for the failing `service/dependency` label pair.
3. Check `docker compose ps` and service logs.

Recovery:

1. Restart the failed dependency or service.
2. Re-run `make health`.
3. Re-run `make smoke-phase7` to confirm headers, metrics, and admin ops still function.

## AI Degradation

Symptoms:

- AI ask endpoints return elevated 5xx rates
- `EduCorpAIErrorRate` alert fires

Checks:

1. Open the platform dashboard and inspect AI request failures.
2. Call `/api/v1/ai/health/ready`.
3. Exercise `/api/v1/ai/ask` manually or with `make smoke-phase5`.

Recovery:

1. Restore the LLM or vector dependency.
2. Confirm graceful error responses instead of generic failures.
3. Re-run the AI smoke and a short load test.

## Load Testing

Run a representative local load test:

```bash
make load-test USERS=20 SPAWN_RATE=4 RUN_TIME=2m
```

Covered flows:

- Catalog/search browse
- Course detail reads
- Enrollment create attempts
- AI ask requests

## Dependency Audit

Run:

```bash
make dep-audit
```

This audits the shared package and all service packages using `pip-audit` through the workspace environment.
