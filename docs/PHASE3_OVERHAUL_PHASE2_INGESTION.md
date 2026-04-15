# Phase 3 Overhaul - Phase 2 Ingestion And Indexing

## Objective

Build a cheap, robust extraction and indexing pipeline that handles both text-rich content and image-heavy PDF slides.

This phase is where the repo moves from a basic text extractor to a real artifact-driven ingestion pipeline.

## Target Outcome

- Text-first documents are processed without unnecessary API cost.
- Image-heavy PDF pages get OCR rescue.
- Only low-confidence pages go to NanoGPT for visual enrichment.
- Chunking is deterministic, citation-safe, and version-aware.
- Embeddings are generated through OpenAI `text-embedding-3-small` with caching.
- Qdrant stores only active overhaul vectors in `course_chunks_v2`.

## Provider Strategy

### What Uses Real External APIs

- OpenAI embeddings: always for final chunk embeddings
- NanoGPT `google/gemma-4-31b-it`: only for selective visual enrichment on low-confidence, image-heavy pages

### What Must Stay Local And Cheap

- PDF native text extraction
- quick document heuristics
- OCR rescue
- content hashing
- chunking
- caching

## Design Rules

- Do not send every page to NanoGPT.
- Do not embed duplicate chunk text twice.
- Do not chunk across page boundaries for slide decks.
- Do not make Qdrant the source of truth for readiness.
- Do not let machine-generated visual summaries overwrite extracted source text.

## Extraction Decision Tree

Apply this exact decision tree for each asset.

### For PDF Assets

1. Extract native text and page structure first.
2. For each page, compute:
   - extracted text length
   - image density or raster density estimate
   - text coverage ratio
   - duplicate-page probability
3. If page text is strong enough, keep native text only.
4. If page text is weak, render the page to PNG.
5. Run OCR on the rendered PNG.
6. Recompute confidence.
7. If confidence is still low and the page is image-heavy, send that page image to NanoGPT for a short visual summary.

### For PPTX Assets

Keep Phase 2 simple.

- extract slide text and speaker notes
- do not add full slide rendering unless it becomes necessary after PDF support is proven
- treat PDF slide decks as the primary visual-first target for this overhaul

### For TXT, MD, DOCX, VTT, SRT

- use local extraction only
- do not call OCR or NanoGPT

## Canonical Record Model

Before chunking, create a canonical page or slide record with these fields:

- `version_id`
- `asset_id`
- `source_type`
- `page_or_slide_number`
- `module_id`
- `module_title`
- `asset_title`
- `native_text`
- `ocr_text`
- `visual_summary`
- `has_visual_summary`
- `text_confidence`
- `visual_confidence`
- `content_hash`
- `flags`

Store canonical records as JSON artifacts in MinIO and register them in `publishing.version_artifacts`.

## Chunking Rules

- Default chunk target: 300 to 600 tokens
- Hard chunk cap: 800 tokens
- Overlap: 60 to 100 tokens within the same page or section only
- For slide decks: prefer one chunk per slide unless the slide is unusually dense
- Strip repeated headers, footers, dates, and slide numbers before chunking
- Include provenance in every chunk

Every chunk must carry:

- `chunk_hash`
- `version_id`
- `course_id`
- `module_id`
- `asset_id`
- `page_or_slide_number`
- `module_title`
- `asset_title`
- `source_type`
- `quality_score`
- `content_sources_used`

## Embedding And Vector Rules

### Embeddings

- Provider: OpenAI
- Model: `text-embedding-3-small`
- Cache key: `chunk_hash + provider + model`
- Never re-embed unchanged chunk text

### Qdrant

- New collection name: `course_chunks_v2`
- Publishing service owns writes
- Search service only reads
- Payload must include at least:
  - `course_id`
  - `version_id`
  - `module_id`
  - `asset_id`
  - `page_or_slide_number`
  - `module_title`
  - `asset_title`
  - `chunk_index`
  - `quality_score`
  - `source_type`

## MinIO Artifact Layout

Add these version-scoped prefixes:

```text
course-assets/
  versions/<version_id>/extraction/pages/<asset_id>/<page>.json
  versions/<version_id>/rendered-pages/<asset_id>/<page>.png
  versions/<version_id>/ocr/<asset_id>/<page>.json
  versions/<version_id>/vision/<asset_id>/<page>.json
  versions/<version_id>/chunks/chunks.jsonl
  versions/<version_id>/reports/quality-report.json
```

## Cost Guardrails

These values should exist as settings and must be operator-visible.

- `VISUAL_ENRICHMENT_ENABLED=true`
- `VISUAL_ENRICHMENT_MAX_PAGES_PER_ASSET=10`
- `VISUAL_ENRICHMENT_MAX_PERCENT_PER_ASSET=0.20`
- `LOW_TEXT_THRESHOLD_CHARS=250`
- `OCR_CONFIDENCE_THRESHOLD=0.70`
- `VISUAL_CONFIDENCE_THRESHOLD=0.65`

If an asset exceeds the allowed visual-enrichment budget, the version must return to `REVIEW_REQUIRED` with a clear operator warning instead of silently overspending.

## Exact Implementation Sequence

### Step 2.1 - Refactor extraction service into stages

Split the current extractor into separate concerns:

- native extraction
- page heuristics
- OCR rescue
- NanoGPT visual enrichment
- canonical record builder

### Step 2.2 - Add PDF-first heuristics

For each PDF page calculate:

- native text length
- text block count
- presence of large raster regions
- whether the page is effectively image-only

### Step 2.3 - Add OCR rescue path

- Render only flagged pages.
- Run OCR on those flagged pages.
- Store OCR results as artifacts.
- Keep raw OCR separate from canonical merged text.

### Step 2.4 - Add NanoGPT visual enrichment adapter

Only call NanoGPT when both of these are true:

- OCR still leaves confidence below threshold
- the page is image-heavy enough to justify a paid call

Prompt contract:

- short JSON only
- no rewriting of lecture content
- max one short factual summary plus diagram terms

### Step 2.5 - Build canonical page records

- Merge native text, OCR text, and optional visual summary.
- Generate `content_hash` after normalization.
- Register each canonical page record as an artifact.

### Step 2.6 - Replace naive chunking

- Build chunk boundaries from page or slide records.
- Remove duplicate boilerplate.
- Attach provenance and quality metadata.

### Step 2.7 - Add embedding cache

- Use OpenAI `text-embedding-3-small`.
- Persist cached embeddings by `chunk_hash`.
- Batch requests.
- Add rate-limit backoff and clear error logging.

### Step 2.8 - Add version-safe Qdrant writes

- Upsert to `course_chunks_v2`.
- Store the version ID in every point.
- Add explicit cleanup on retry or cancellation so stale points do not survive.

### Step 2.9 - Add quality reporting

Each publish run must produce a machine-readable report with:

- total pages
- OCR pages count
- NanoGPT pages count
- duplicate chunks removed
- total chunks
- total embeddings reused
- total embeddings created
- low-confidence pages count

### Step 2.10 - Add tests before moving to Phase 3

Required tests:

- PDF heuristic classification test
- OCR-only fallback test
- selective NanoGPT invocation test
- chunk provenance test
- embedding cache reuse test
- Qdrant retry cleanup test

## Files Expected To Change

Core files likely to change in this phase:

- `services/publishing/app/services/extraction_service.py`
- `services/publishing/app/services/chunking_service.py`
- `services/publishing/app/services/embedding_service.py`
- `services/publishing/app/services/qdrant_service.py`
- `services/publishing/app/activities/publishing_activities.py`
- `services/publishing/app/workflows/publish_course.py`
- `services/publishing/app/workflows/types.py`
- `services/publishing/app/models/*.py`
- `services/publishing/app/repositories/*.py`
- `services/publishing/pyproject.toml`
- `infra/docker/Dockerfile.service`
- `.env.example`

Expected new service modules:

- `services/publishing/app/services/ocr_service.py`
- `services/publishing/app/services/visual_enrichment_service.py`
- `services/publishing/app/services/page_quality_service.py`
- `services/publishing/app/services/artifact_service.py`

## Manual Validation Gate

Do not start Phase 3 until every item below passes.

### Validation A - Text-first PDF should stay cheap

1. Publish a text-rich PDF.
2. Inspect the quality report.
3. Confirm OCR page count is zero or near zero.
4. Confirm NanoGPT page count is zero.

### Validation B - Image-heavy PDF should use selective rescue

1. Publish an image-heavy PDF slide deck.
2. Confirm only flagged pages were rendered to PNG.
3. Confirm only low-confidence flagged pages went to NanoGPT.
4. Confirm the number of paid visual calls stays within the configured budget.

### Validation C - MinIO artifact proof

Use either the console or `mc`.

```bash
bash -c "mc alias set local http://localhost:9000 educorp educorp_dev && mc tree local/course-assets/versions/<version_id>"
```

Confirm the version contains:

- page extraction JSON artifacts
- OCR artifacts when expected
- vision artifacts only for flagged pages
- chunk JSON output
- a quality report

### Validation D - Qdrant proof

```bash
bash -c "curl -s http://localhost:6333/collections/course_chunks_v2 | jq ."
```

Confirm the collection exists and that point payloads include `version_id` and `page_or_slide_number`.

### Validation E - Retry cleanup proof

1. Force a publish failure after chunks are created but before final success.
2. Retry the version.
3. Confirm point counts and chunk counts do not duplicate.

## Exit Criteria

- Hybrid ingestion works for both text-heavy and image-heavy PDF assets.
- NanoGPT calls are selective and budgeted.
- OpenAI embeddings are real, cached, and version-safe.
- Qdrant points are version-scoped and clean on retry.
- Required Phase 2 tests exist and pass.
