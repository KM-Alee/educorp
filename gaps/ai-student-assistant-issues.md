# AI Student Assistant Issues

## Scope

This file covers the student-facing Phase 5 Q&A system.

Primary paths audited:

- `services/ai/app/services/qa_graph.py`
- `services/ai/app/services/qa_streaming.py`
- `services/ai/app/api/v1/ask.py`
- `services/ai/app/services/retriever.py`
- AI tests

## What Is Already Present

- non-streaming ask endpoint exists
- streaming ask endpoint exists
- LangGraph-based pipeline exists with validate/retrieve/assess/generate/refuse/clarify/cite/log nodes
- Redis-backed response cache exists
- Redis-backed rate limiter exists
- Qdrant retrieval exists

The main issue is not absence. It is that key correctness guarantees are not yet real.

## Confirmed Gaps

### 1. Clarification path is effectively unreachable

Evidence:

- `services/ai/app/services/qa_graph.py:194-218`
- `services/ai/app/services/qa_graph.py:370-375`

Problem:

- `_assess()` always sets `is_ambiguous` to `False`
- the graph contains a clarify branch, but the branch is never selected in practice

Required fix:

- implement actual ambiguity detection criteria
- define what retrieval or intent conditions should route to clarification instead of answer/refusal

### 2. Clarification follow-up is not stateful

Evidence:

- `services/ai/app/api/v1/ask.py` clarify route ignores the original query state according to the audit

Problem:

- Phase 5 implies a continuation of a previous ambiguous interaction
- current behavior is effectively just another fresh question submission

Required fix:

- persist or reconstruct original query context
- use `original_query_id` meaningfully
- define expiration and validation rules for follow-up clarification

### 3. Citation validity is not enforced

Evidence:

- `services/ai/app/services/qa_graph.py:268-273`
- `services/ai/app/services/citation_service.py`

Problem:

- invalid citation references are only logged
- the system can return answers whose citations do not faithfully map to retrieved chunks

Required fix:

- implement one of these behaviors:
  - repair answer/citation mismatch before returning
  - refuse invalid answers
  - rerun generation with stricter formatting
- do not merely warn and return potentially invalid citations

### 4. Retrieval gating does not fully match the intended contract

Evidence:

- `services/ai/app/services/retriever.py:30-55`
- `services/publishing/app/services/qdrant_service.py:93-107`

Problem:

- retriever filters by `course_id` and `version_id` only
- payload does not store `version_status`
- documented Phase 5 language expects tighter READY-version semantics and explicit version-status gating

Required fix:

- align Qdrant payload design and retrieval filters with the intended retrieval contract

### 5. Streaming implementation diverges from the main Q&A state machine

Problem:

- streaming logic is implemented separately rather than reusing the main graph semantics
- this creates drift in refusal behavior, clarification handling, and logging semantics

Required fix:

- choose one source of truth for student Q&A logic
- ideally share the same decisioning core for streaming and non-streaming modes

### 6. Streaming behavior is incomplete for real clients

Problem:

- client disconnect handling is not robust
- event taxonomy is thinner than the documented behavior
- refusal and clarification semantics are not clearly emitted as typed stream outcomes

Required fix:

- define stream event contract explicitly
- handle disconnects, done, error, refusal, clarification, and citations consistently

### 7. Admin rate-limit bypass is missing

Evidence:

- Phase 5 requires admin to be unlimited for testing
- current logic in `services/ai/app/services/qa_graph.py:128-138` uses only student vs instructor scopes

Required fix:

- implement explicit admin bypass semantics in validation/rate limiting

## Risks

### Event loop blocking risk

Evidence:

- Qdrant client usage is synchronous inside async paths

Risk:

- under load, AI latency and concurrency can degrade significantly

### Over-refusal risk

Evidence:

- current thresholding appears stricter than the design examples

Risk:

- valid course questions may be refused too often

## Test Gaps

Current tests mainly monkeypatch service methods and route wiring. They do not prove:

- real clarification routing
- refusal behavior correctness
- citation validation correctness
- entitlement enforcement against realistic data
- streaming contract correctness
- rate limiting behavior

## Implementation Plan

1. Make clarification logic real and stateful.
2. Enforce citation validity instead of only logging warnings.
3. Unify streaming and non-streaming decision semantics.
4. Align retrieval payload/filtering with the Phase 5 contract.
5. Add admin bypass and refine thresholds.
6. Add tests for refusal, clarification, citations, entitlement, rate limiting, and streaming.

## Exit Criteria

- ambiguous questions can reach a real clarification path
- follow-up clarification uses prior query context
- returned citations are valid against retrieved chunks
- streaming and non-streaming share the same decision semantics
- rate limiting and entitlement behave as specified
- tests cover real Phase 5 student assistant behavior
