# Infrastructure Recommendations

## Intent

This file defines the infrastructure and operational remediation required before treating Phase 4 and 5 as truly runnable. The current stack has most dependencies present, but startup, readiness, migrations, test execution, and AI support are too fragile for reliable end-to-end work.

## High-Impact Findings

### 1. Container healthchecks are pointed at the wrong path

Evidence:

- `infra/docker/Dockerfile.service:77-78` probes `http://localhost:8000/health/live`
- services mount health routes under API prefixes, for example:
  - `services/auth/app/main.py`
  - `services/ai/app/main.py`
  - `services/publishing/app/main.py`

Why this matters:

- containers can report unhealthy even while the app is actually serving under Traefik
- startup orchestration and operational trust degrade immediately

Required fix:

- standardize one of these approaches:
  - expose root-level `/health/live` and `/health/ready` in every service, or
  - parameterize the healthcheck path per service in Compose
- do not leave Docker health semantics inconsistent with app routing

### 2. Readiness endpoints are shallow and do not prove runtime viability

Evidence:

- `services/progress/app/api/v1/__init__.py:34-37`
- `services/enrollment/app/api/v1/__init__.py:36-39`
- `services/ai/app/api/v1/__init__.py` returns static ready responses

Why this matters:

- the system can claim readiness while DB, Redis, Mongo, Qdrant, Kafka, Temporal, or MinIO are unavailable
- Phase 4 and 5 are dependency-heavy; shallow readiness is not operationally honest

Required fix:

- add dependency-aware readiness checks per service
- minimum expected checks:
  - enrollment: PostgreSQL, Redis
  - progress: PostgreSQL
  - ai: PostgreSQL, Redis, Mongo, Qdrant, optional Kafka health classification
  - publishing: PostgreSQL, Temporal, Qdrant, MinIO, optional Kafka classification
- return structured degraded states if you intentionally permit partial startup

### 3. `ai-service` is missing a Compose dependency on MongoDB

Evidence:

- `docker-compose.yml:587-608` includes PostgreSQL, Redis, Qdrant but not Mongo
- `services/ai/app/main.py` initializes Mongo-backed job storage on startup

Why this matters:

- AI instructor job endpoints can fail or race during stack startup

Required fix:

- add `mongodb` as an explicit `depends_on` dependency for `ai-service`
- verify startup ordering for AI job APIs and Mongo-backed repositories

### 4. Kafka topic provisioning does not include AI usage events

Evidence:

- topic bootstrap in Compose does not include `ai.usage`
- `services/ai/app/config.py` and `services/ai/app/services/event_emitter.py` emit to `ai.usage`
- Kafka auto topic creation is disabled

Why this matters:

- AI usage events silently fail or get dropped, undermining Phase 5 logging and later analytics work

Required fix:

- add `ai.usage` to Kafka topic initialization
- validate topic creation in startup automation
- add smoke coverage that confirms produce succeeds

### 5. Migration orchestration is fail-soft when it should be fail-fast

Evidence:

- `Makefile:93-104` prints warnings and continues on migration failure
- `scripts/start-stack.sh` also swallows migration issues

Why this matters:

- a partially migrated system can boot and then fail later in confusing ways
- this is especially dangerous for Phase 4/5 where multiple services assume new schemas exist

Required fix:

- make stack startup fail immediately if required migrations fail
- separate optional services from mandatory service migrations if needed
- emit a clear summary of which services migrated and which blocked startup

### 6. Test-running environments are not provisioned correctly

Evidence:

- `Dockerfile.service` installs runtime service deps only
- `Makefile:120-130` runs `pytest` inside service containers
- root dev deps include test libraries, but service containers do not inherit them
- `pytest-cov` is not present even though `--cov` is used

Why this matters:

- `make test` and `make test-coverage` are not trustworthy as advertised

Required fix:

- choose one of these patterns and standardize it:
  - install test extras in service containers used for test targets, or
  - run tests from a dedicated dev/test image, or
  - run tests outside containers with a supported local workflow
- add `pytest-cov` if coverage targets remain

### 7. There is no local/mock AI provider strategy for deterministic Phase 5 validation

Evidence:

- `.env.example` and service configs point to external model providers with placeholder credentials
- both publishing embeddings and AI Q&A depend on external AI capabilities

Why this matters:

- Phase 5 cannot be reproducibly validated from a fresh local stack without external credentials
- CI and contributor workflows will remain unstable

Required fix:

- define a local development AI mode
- acceptable approaches:
  - mock OpenAI-compatible local server
  - deterministic fake LLM/embedding service behind config flag
  - profile-specific provider swap for local and CI
- document the expected mode in `.env.example`, `README`, and test docs

### 8. Seed and smoke tooling does not prepare a Phase 4/5-ready environment

Evidence:

- `make seed` seeds auth only
- current seed tooling does not produce a READY course/version/chunks path suitable for enrollment + AI testing
- existing E2E helper remains Phase 3 oriented

Why this matters:

- engineers cannot quickly validate the actual user journeys Phase 4/5 depend on

Required fix:

- create deterministic seed/smoke support for:
  - admin, instructor, student accounts
  - at least one published READY course
  - enrollable metadata and modules
  - AI retrievable chunks in Qdrant
- add smoke journeys for:
  - enroll -> progress -> complete -> certificate
  - ask question -> get cited answer

## Overall Infrastructure Update Recommendation

Do one focused infra-hardening pass before further Phase 4/5 feature patching.

The recommended sequence is:

1. Fix healthchecks and dependency-aware readiness.
2. Make migrations and startup scripts fail-fast.
3. Add missing runtime dependencies in Compose, especially Mongo for AI.
4. Add missing Kafka topics, especially `ai.usage`.
5. Establish a local/mock AI provider mode.
6. Fix test environments so declared test commands actually work.
7. Add deterministic seed + smoke coverage for one real Phase 4 path and one real Phase 5 path.
8. Reconcile docs so the repo promise matches actual runtime behavior.

## Deliverables

- corrected Docker healthchecks
- dependency-aware readiness endpoints
- fail-fast migration/startup scripts
- updated Compose dependency graph
- updated Kafka topic initialization
- documented local AI provider strategy
- working `make test` and `make test-coverage`
- deterministic Phase 4/5 smoke scripts

## Exit Criteria

- `make up-app` produces a stack whose health status is trustworthy
- failing migrations stop startup
- AI service reliably starts with all required dependencies
- AI events publish successfully to a provisioned topic
- a fresh contributor can validate at least one Phase 4 and one Phase 5 journey locally
