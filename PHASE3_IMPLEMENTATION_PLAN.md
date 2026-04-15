# EduCorp - Phase 3 Overhaul Overview

This document replaces the old single-pass Phase 3 plan.

The repo already has a working publish path, a Temporal worker, a search service, and a frontend publishing screen. The problem is not total absence of Phase 3. The problem is that the current implementation is too direct, too mutable, and too weak for real production publishing of lecture material, especially PDF slide decks with lots of images.

The overhaul is split into three execution phases. Each phase is designed for an AI coding agent to implement, but each phase also ends with a mandatory human validation gate before the next phase starts.

## Why The Overhaul Is Necessary

- The current publishing workflow reads mutable draft state while a publish is running.
- The current workflow passes large in-memory payloads between Temporal activities instead of persisting artifacts and passing IDs.
- The current extraction path is mostly text-only and does not handle image-heavy PDF slides well.
- The current embedding configuration still points at placeholder or incorrect defaults.
- The current implementation is thin on operator review, cost control, and end-to-end proof with real course files.

## Non-Negotiable Design Rules

- Do not commit external API secrets to the repo.
- MinIO remains the canonical object store for raw assets and derived publishing artifacts.
- Temporal orchestrates IDs and state transitions, not large blobs.
- Course drafts remain mutable in the course service; published versions become immutable snapshots in the publishing service.
- Publishing owns Qdrant writes. Search only reads from Qdrant.
- Local extraction comes first. Real external APIs are used only where they add clear value.
- Every phase ends with human validation. No skipping.

## External Systems In Scope

### MinIO

- Console: http://localhost:9001
- Dev access key: educorp
- Dev secret key: educorp_dev
- Bucket: course-assets

### Temporal

- UI: http://localhost:8088
- Namespace: educorp
- Task queue to keep using: publishing

### Qdrant

- API: http://localhost:6333
- Use a new collection for the overhaul: course_chunks_v2

### Real Provider Setup

Use locally supplied secrets only. Do not place real provider keys in tracked files.

- NanoGPT base URL: https://nano-gpt.com/api/v1
- NanoGPT model: google/gemma-4-31b-it
- OpenAI embedding model: text-embedding-3-small

The implementation work for this overhaul must convert the repo from generic `LLM_*` and `EMBEDDING_*` placeholders into explicit provider configuration with clear local-only secret handling.

## How To Use This Overhaul Plan

1. Complete [Phase 1](docs/PHASE3_OVERHAUL_PHASE1_FOUNDATION.md).
2. Stop and perform the full human validation checklist.
3. Complete [Phase 2](docs/PHASE3_OVERHAUL_PHASE2_INGESTION.md).
4. Stop and perform the full human validation checklist.
5. Complete [Phase 3](docs/PHASE3_OVERHAUL_PHASE3_SEARCH_AND_E2E.md).
6. Stop and perform the full human validation checklist, including the dummy-course publish run.

## Deliverables By Phase

### Phase 1

- Immutable publish manifest and artifact model
- Course-to-publishing snapshot boundary
- Human preflight gate before real processing
- Correct provider env layout without committed secrets
- Temporal workflow refactored to pass IDs, not large payloads

### Phase 2

- Hybrid extraction for text-first and image-heavy PDFs
- Cheap OCR rescue path plus selective NanoGPT visual enrichment
- Content hashing, artifact caching, chunk hashing, embedding caching
- Version-scoped MinIO artifacts and version-scoped Qdrant indexing

### Phase 3

- Activation and approval flow
- Better keyword and semantic search
- Search-safe citations and source metadata
- Operator cleanup and retention tasks
- Dummy-course end-to-end publish run driven by an AI agent and validated by a human

## Strict Operator Rule

If any manual validation item fails, the phase is not complete. Fix the failing items before moving forward.

## Detailed Phase Docs

- [Phase 1 Foundation](docs/PHASE3_OVERHAUL_PHASE1_FOUNDATION.md)
- [Phase 2 Ingestion](docs/PHASE3_OVERHAUL_PHASE2_INGESTION.md)
- [Phase 3 Search And E2E](docs/PHASE3_OVERHAUL_PHASE3_SEARCH_AND_E2E.md)
