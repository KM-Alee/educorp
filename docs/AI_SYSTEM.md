# EduCorp — AI System Design

## 1. Overview

The AI subsystem provides two capabilities:
1. **Student Q&A** — RAG-based contextual answers with citations, scoped to enrolled course content
2. **Instructor Enhancement** — AI-generated summaries, objectives, quizzes, and glossaries from course material

Both are built on a shared RAG (Retrieval-Augmented Generation) pipeline using LangChain and LangGraph, backed by Qdrant for vector retrieval and an OpenAI-compatible LLM provider (NanoGPT).

```
┌──────────────────────────────────────────────────────────┐
│                     AI Service                            │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ Q&A Chain  │  │ Enhance    │  │ Shared Components  │ │
│  │ (Student)  │  │ Chain      │  │                    │ │
│  │            │  │(Instructor)│  │ - Retriever        │ │
│  │ LangGraph  │  │            │  │ - Embedding Client │ │
│  │ StateMach. │  │ LangChain  │  │ - Citation Builder │ │
│  │            │  │ Chains     │  │ - Token Counter    │ │
│  └──────┬─────┘  └─────┬──────┘  │ - Rate Limiter    │ │
│         │               │         │ - Cache Layer     │ │
│         └───────┬───────┘         └────────┬──────────┘ │
│                 │                          │             │
│                 ▼                          ▼             │
│         ┌──────────────┐          ┌──────────────┐      │
│         │  LLM Client  │          │   Qdrant     │      │
│         │  (NanoGPT)   │          │   Client     │      │
│         └──────────────┘          └──────────────┘      │
└──────────────────────────────────────────────────────────┘
```

## 2. Embedding Pipeline (Publishing Phase)

### 2.1 Text Extraction

| Asset Type | Extractor | Library |
|-----------|-----------|---------|
| PDF | `pdfplumber` | pdfplumber (Python) |
| DOCX | `python-docx` | python-docx |
| PPTX | `python-pptx` | python-pptx |
| TXT/MD | Direct read | Built-in |
| VTT/SRT | Subtitle parser | webvtt-py / pysrt |

Each extractor produces a `ExtractedDocument`:
```python
@dataclass
class ExtractedDocument:
    asset_id: str
    module_id: str
    raw_text: str
    pages: list[PageContent]  # page-level text for PDFs
    language: str  # detected via langdetect
    metadata: dict  # page_count, slide_count, etc.
```

### 2.2 Chunking Strategy

**Method**: Recursive character-based splitting with overlap, respecting sentence boundaries.

**Configuration**:
```python
CHUNK_SIZE = 512          # tokens (roughly 2000 chars)
CHUNK_OVERLAP = 64        # tokens overlap between chunks
MIN_CHUNK_SIZE = 50       # tokens — discard tiny trailing chunks
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
```

**Metadata per chunk**:
```python
@dataclass
class ChunkMetadata:
    chunk_id: str           # UUID
    course_id: str
    version_id: str
    module_id: str
    module_title: str
    asset_id: str
    asset_title: str
    chunk_index: int        # Position within the asset
    char_start: int
    char_end: int
    token_count: int
    page_number: int | None  # For PDFs
    section_title: str | None  # If detectable from headings
```

**Why this approach**:
- Token-based sizing ensures consistent LLM context windows
- Overlap prevents information loss at chunk boundaries
- Sentence-boundary respect keeps semantic coherence
- Rich metadata enables precise citations

### 2.3 Embedding Generation

**Provider**: OpenAI-compatible embeddings API (via NanoGPT or direct)
**Model**: `text-embedding-ada-002` (1536 dimensions) or configurable
**Batch size**: 100 chunks per API call
**Rate limiting**: Respect provider rate limits with exponential backoff

```python
async def generate_embeddings(chunks: list[Chunk]) -> list[EmbeddingResult]:
    """Generate embeddings in batches with retry logic."""
    results = []
    for batch in batched(chunks, EMBEDDING_BATCH_SIZE):
        texts = [c.text for c in batch]
        embeddings = await embedding_client.embed(texts)
        results.extend(zip(batch, embeddings))
    return results
```

### 2.4 Qdrant Indexing

**Collection setup**:
```python
qdrant_client.create_collection(
    collection_name="course_chunks",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    ),
    # Payload indexes for filtering
    optimizers_config=OptimizersConfigDiff(
        indexing_threshold=20000
    )
)

# Create payload indexes
qdrant_client.create_payload_index("course_chunks", "course_id", PayloadSchemaType.KEYWORD)
qdrant_client.create_payload_index("course_chunks", "version_id", PayloadSchemaType.KEYWORD)
qdrant_client.create_payload_index("course_chunks", "version_status", PayloadSchemaType.KEYWORD)
qdrant_client.create_payload_index("course_chunks", "module_id", PayloadSchemaType.KEYWORD)
```

**Upsert pattern**:
```python
points = [
    PointStruct(
        id=chunk.chunk_id,
        vector=embedding,
        payload={
            "course_id": chunk.course_id,
            "version_id": chunk.version_id,
            "version_status": "READY",  # Set on finalization
            "module_id": chunk.module_id,
            "module_title": chunk.module_title,
            "asset_id": chunk.asset_id,
            "asset_title": chunk.asset_title,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
        }
    )
    for chunk, embedding in embedding_results
]
qdrant_client.upsert("course_chunks", points=points, wait=True)
```

**Version transition**: When a new version becomes READY:
1. New chunks are inserted with `version_status: "READY"`
2. Old version's chunks are updated to `version_status: "SUPERSEDED"`
3. This is done atomically in the Temporal finalize step

## 3. Student Q&A — LangGraph State Machine

### 3.1 Architecture

The Q&A system uses LangGraph to model the answer generation as a state machine with explicit decision nodes:

```
                    ┌───────────┐
                    │   START   │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │ Validate  │ → Check entitlement, rate limit
                    │  Input    │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  Retrieve │ → Qdrant semantic search
                    │  Chunks   │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  Assess   │ → Enough context? Relevant?
                    │ Relevance │
                    └─────┬─────┘
                     ╱    │    ╲
                    ╱     │     ╲
          ┌────────┐ ┌───▼────┐ ┌─────────┐
          │ Refuse │ │Generate│ │ Clarify │
          │(no ctx)│ │ Answer │ │  (ask   │
          └───┬────┘ └───┬────┘ │  user)  │
              │          │      └────┬────┘
              │    ┌─────▼─────┐    │
              │    │  Build    │    │
              │    │ Citations │    │
              │    └─────┬─────┘    │
              │          │          │
              └────┬─────┘──────┬───┘
                   │            │
             ┌─────▼─────┐     │
             │   Log &   │◀────┘
             │   Emit    │
             └─────┬─────┘
                   │
             ┌─────▼─────┐
             │    END     │
             └───────────┘
```

### 3.2 LangGraph State

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END


class QAState(TypedDict):
    # Input
    course_id: str
    question: str
    module_id: str | None
    user_id: str
    version_id: str

    # Retrieval
    chunks: list[dict]
    relevance_scores: list[float]

    # Assessment
    has_sufficient_context: bool
    is_ambiguous: bool

    # Output
    answer: str | None
    citations: list[dict]
    confidence: str  # 'high', 'medium', 'low'
    response_type: str  # 'answer', 'refusal', 'clarification'

    # Metadata
    query_id: str
    tokens_used: dict
    latency_ms: int


def build_qa_graph() -> StateGraph:
    graph = StateGraph(QAState)

    graph.add_node("validate", validate_input)
    graph.add_node("retrieve", retrieve_chunks)
    graph.add_node("assess", assess_relevance)
    graph.add_node("generate", generate_answer)
    graph.add_node("refuse", generate_refusal)
    graph.add_node("clarify", generate_clarification)
    graph.add_node("build_citations", build_citations)
    graph.add_node("log_and_emit", log_and_emit)

    graph.set_entry_point("validate")
    graph.add_edge("validate", "retrieve")
    graph.add_edge("retrieve", "assess")

    graph.add_conditional_edges("assess", route_after_assessment, {
        "generate": "generate",
        "refuse": "refuse",
        "clarify": "clarify",
    })

    graph.add_edge("generate", "build_citations")
    graph.add_edge("build_citations", "log_and_emit")
    graph.add_edge("refuse", "log_and_emit")
    graph.add_edge("clarify", "log_and_emit")
    graph.add_edge("log_and_emit", END)

    return graph.compile()
```

### 3.3 Retrieval Node

```python
async def retrieve_chunks(state: QAState) -> dict:
    """Retrieve top-k relevant chunks from Qdrant."""
    query_embedding = await embedding_client.embed([state["question"]])

    filter_conditions = [
        FieldCondition(key="course_id", match=MatchValue(value=state["course_id"])),
        FieldCondition(key="version_status", match=MatchValue(value="READY")),
    ]

    if state.get("module_id"):
        filter_conditions.append(
            FieldCondition(key="module_id", match=MatchValue(value=state["module_id"]))
        )

    results = await qdrant_client.search(
        collection_name="course_chunks",
        query_vector=query_embedding[0],
        query_filter=Filter(must=filter_conditions),
        limit=TOP_K,  # 10
        with_payload=True,
        score_threshold=RELEVANCE_THRESHOLD,  # 0.3
    )

    return {
        "chunks": [hit.payload for hit in results],
        "relevance_scores": [hit.score for hit in results],
    }
```

### 3.4 Assessment & Routing

```python
RELEVANCE_THRESHOLD = 0.3    # Minimum cosine similarity
MIN_CHUNKS_FOR_ANSWER = 2    # Need at least 2 relevant chunks
HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.5


def assess_relevance(state: QAState) -> dict:
    chunks = state["chunks"]
    scores = state["relevance_scores"]

    if not chunks or len(chunks) < MIN_CHUNKS_FOR_ANSWER:
        return {"has_sufficient_context": False, "is_ambiguous": False}

    avg_score = sum(scores) / len(scores)
    top_score = max(scores) if scores else 0

    if top_score < RELEVANCE_THRESHOLD:
        return {"has_sufficient_context": False, "is_ambiguous": False}

    # Check if question is too vague (high variance in scores, no clear top match)
    if len(scores) > 3 and top_score < 0.4 and max(scores) - min(scores) < 0.1:
        return {"has_sufficient_context": True, "is_ambiguous": True}

    confidence = "high" if avg_score >= HIGH_CONFIDENCE_THRESHOLD else \
                 "medium" if avg_score >= MEDIUM_CONFIDENCE_THRESHOLD else "low"

    return {
        "has_sufficient_context": True,
        "is_ambiguous": False,
        "confidence": confidence,
    }


def route_after_assessment(state: QAState) -> str:
    if not state["has_sufficient_context"]:
        return "refuse"
    if state["is_ambiguous"]:
        return "clarify"
    return "generate"
```

### 3.5 Answer Generation

```python
SYSTEM_PROMPT = """You are a course assistant for "{course_title}".
Your job is to answer the student's question using ONLY the provided course material excerpts.

RULES:
1. ONLY use information from the provided excerpts. Never use external knowledge.
2. If the excerpts don't contain enough information, say so clearly.
3. For each claim you make, reference the source excerpt by its [number].
4. Be concise and educational.
5. If the question is about something not covered in the course, politely decline.
6. Never make up information. Never hallucinate citations.
"""

CONTEXT_TEMPLATE = """
Here are relevant excerpts from the course material:

{formatted_chunks}

---
Student's question: {question}
"""


async def generate_answer(state: QAState) -> dict:
    chunks = state["chunks"]
    formatted = "\n\n".join(
        f"[{i+1}] (Module: {c['module_title']}, Asset: {c['asset_title']}"
        f"{f', Page {c[\"page_number\"]}' if c.get('page_number') else ''})\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(course_title=state.get("course_title", ""))},
        {"role": "user", "content": CONTEXT_TEMPLATE.format(
            formatted_chunks=formatted,
            question=state["question"]
        )}
    ]

    response = await llm_client.chat_completion(
        messages=messages,
        temperature=0.1,  # Low temperature for factual answers
        max_tokens=1500,
        stream=False,
    )

    return {
        "answer": response.content,
        "tokens_used": {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        }
    }
```

### 3.6 Streaming Implementation (SSE)

```python
from fastapi import Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse


async def stream_qa_response(request: Request, state: QAState):
    """Stream the Q&A response via SSE."""

    async def event_generator():
        # Run retrieval and assessment synchronously first
        state = await run_retrieval_and_assessment(state)

        if state["response_type"] == "refusal":
            yield {"event": "refusal", "data": json.dumps({"message": state["answer"]})}
            yield {"event": "done", "data": json.dumps({"query_id": state["query_id"]})}
            return

        # Stream LLM response
        chunks_context = format_chunks_for_prompt(state["chunks"])
        messages = build_messages(chunks_context, state["question"])

        async for token in llm_client.chat_completion_stream(messages=messages, temperature=0.1):
            if await request.is_disconnected():
                break
            yield {"event": "token", "data": json.dumps({"text": token})}

        # Send citations after answer is complete
        for citation in state["citations"]:
            yield {"event": "citation", "data": json.dumps(citation)}

        yield {
            "event": "done",
            "data": json.dumps({
                "query_id": state["query_id"],
                "confidence": state["confidence"],
                "total_citations": len(state["citations"]),
            })
        }

    return EventSourceResponse(event_generator())
```

### 3.7 Citation Building

```python
def build_citations(state: QAState) -> dict:
    """Build structured citations from retrieved chunks referenced in the answer."""
    answer = state["answer"]
    chunks = state["chunks"]
    citations = []

    # Extract reference numbers from answer (e.g., [1], [2])
    import re
    referenced = set(int(m) for m in re.findall(r'\[(\d+)\]', answer))

    for i, chunk in enumerate(chunks):
        if (i + 1) in referenced:
            citations.append({
                "chunk_id": chunk.get("chunk_id", str(i)),
                "module_title": chunk["module_title"],
                "asset_title": chunk["asset_title"],
                "text_snippet": chunk["text"][:200],
                "page_number": chunk.get("page_number"),
            })

    # Validate: if answer references [3] but we only have 2 chunks, flag it
    max_chunk = len(chunks)
    invalid_refs = [r for r in referenced if r > max_chunk or r < 1]
    if invalid_refs:
        # Log warning — potential hallucinated citation
        logger.warning(f"Invalid citation references in answer: {invalid_refs}")

    return {"citations": citations}
```

## 4. Instructor Enhancement Tools

### 4.1 Job Types

| Job Type | Description | Input | Output |
|----------|-------------|-------|--------|
| `summary` | Generate module/course summary | scope, max_length | Structured summary text |
| `objectives` | Learning objectives | scope | List of objectives |
| `quiz` | Quiz questions with answer keys | scope, question_count, types | Questions with answers |
| `glossary` | Key terms and definitions | scope | Term-definition pairs |

### 4.2 Enhancement Chain (LangChain)

```python
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate


ENHANCEMENT_PROMPTS = {
    "summary": ChatPromptTemplate.from_messages([
        ("system", """You are an educational content expert. Generate a clear, structured summary
        of the following course material. The summary should:
        - Highlight key concepts and their relationships
        - Be appropriate for {difficulty} level learners
        - Stay under {max_length} words
        - Reference specific topics from the material"""),
        ("user", "Course material:\n\n{context}\n\nGenerate a summary.")
    ]),

    "objectives": ChatPromptTemplate.from_messages([
        ("system", """You are an instructional designer. Generate learning objectives using
        Bloom's taxonomy. Each objective should:
        - Start with an action verb (Understand, Apply, Analyze, etc.)
        - Be measurable and specific
        - Cover the key topics in the material"""),
        ("user", "Course material:\n\n{context}\n\nGenerate 5-10 learning objectives.")
    ]),

    "quiz": ChatPromptTemplate.from_messages([
        ("system", """You are an assessment expert. Generate quiz questions from the course material.
        Requirements:
        - {question_count} questions
        - Mix of multiple choice and short answer
        - Each question must have a correct answer and explanation
        - Each answer must reference specific material from the excerpts
        - Questions should test understanding, not just recall"""),
        ("user", "Course material:\n\n{context}\n\nGenerate quiz questions.")
    ]),

    "glossary": ChatPromptTemplate.from_messages([
        ("system", """You are a subject matter expert. Extract key terms and provide clear,
        concise definitions based on the course material. Each entry should:
        - Use the definition as given in the material
        - Be understandable at {difficulty} level
        - Include related terms where applicable"""),
        ("user", "Course material:\n\n{context}\n\nGenerate a glossary.")
    ]),
}
```

### 4.3 Async Job Processing

Enhancement jobs run as async tasks managed by the AI service:

```python
# Job lifecycle: QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED

async def process_enhancement_job(job_id: str):
    job = await get_job(job_id)

    try:
        await update_job_status(job_id, "RUNNING")

        # Retrieve relevant chunks
        chunks = await retrieve_chunks_for_scope(
            course_id=job.course_id,
            version_id=job.version_id,
            scope=job.scope,
            module_id=job.module_id,
        )

        # Build context
        context = "\n\n".join(c["text"] for c in chunks)

        # Check token budget
        if count_tokens(context) > MAX_CONTEXT_TOKENS:
            context = truncate_to_token_limit(context, MAX_CONTEXT_TOKENS)

        # Generate
        prompt = ENHANCEMENT_PROMPTS[job.job_type]
        result = await llm_client.chat_completion(
            messages=prompt.format_messages(
                context=context,
                difficulty=job.parameters.get("difficulty", "intermediate"),
                max_length=job.parameters.get("max_length", 500),
                question_count=job.parameters.get("question_count", 10),
            ),
            temperature=0.3,
            max_tokens=3000,
        )

        # Parse and store result
        parsed = parse_enhancement_result(job.job_type, result.content)
        await complete_job(job_id, parsed, tokens_used=result.usage)

    except Exception as e:
        await fail_job(job_id, error_code=classify_error(e), message=str(e))
```

## 5. Safety & Quality Controls

### 5.1 Content Isolation

| Control | Implementation |
|---------|---------------|
| Course-scoped retrieval | Qdrant filter: `course_id` must match |
| Version gating | Qdrant filter: `version_status = "READY"` |
| Entitlement check | Verify enrollment before retrieval |
| No cross-course leakage | System prompt instructs model to use ONLY provided excerpts |
| No unpublished content | Non-READY chunks have `version_status != "READY"` |

### 5.2 Hallucination Prevention

| Technique | Description |
|-----------|-------------|
| Low temperature | `temperature=0.1` for factual Q&A |
| Citation validation | Parse answer for `[n]` references, validate against actual chunks |
| Refusal behavior | If <2 relevant chunks or all scores below threshold, refuse |
| System prompt constraints | Explicit instruction to only use provided material |
| Post-generation validation | Check that every cited chunk actually exists in the retrieval set |

### 5.3 Rate Limiting & Cost Control

```python
# Per-user rate limits
AI_RATE_LIMIT_QUERIES_PER_MIN = 20
AI_RATE_LIMIT_TOKENS_PER_DAY = 100_000

# Per-course daily budget
COURSE_TOKEN_BUDGET_PER_DAY = 500_000

# Per-request token limits
MAX_INPUT_TOKENS = 4000
MAX_OUTPUT_TOKENS = 1500
MAX_CONTEXT_CHUNKS = 10
```

### 5.4 Caching

AI responses are cached in Redis when:
- Same question (normalized) + same course + same version
- Cache key: `ai:cache:{sha256(normalized_question)}:{course_id}:{version_id}`
- TTL: 1 hour
- Cache is invalidated when a new version becomes READY

```python
async def get_cached_response(question: str, course_id: str, version_id: str) -> dict | None:
    normalized = normalize_question(question.lower().strip())
    cache_key = f"ai:cache:{hashlib.sha256(normalized.encode()).hexdigest()}:{course_id}:{version_id}"
    cached = await redis.get(cache_key)
    return json.loads(cached) if cached else None
```

## 6. LLM Client Configuration

### 6.1 Provider Setup

```python
# OpenAI-compatible client for NanoGPT
from openai import AsyncOpenAI

llm_client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL,          # NanoGPT endpoint
    api_key=settings.LLM_API_KEY,
    timeout=30.0,
    max_retries=2,
)

embedding_client = AsyncOpenAI(
    base_url=settings.EMBEDDING_BASE_URL,
    api_key=settings.EMBEDDING_API_KEY,
    timeout=15.0,
    max_retries=3,
)
```

### 6.2 Model Configuration

```python
# Environment-based configuration
LLM_MODEL = "nanogpt-chat"                   # Model name for chat completions
EMBEDDING_MODEL = "text-embedding-ada-002"    # Embedding model
EMBEDDING_DIMENSION = 1536                     # Vector dimensions

# Fallback models (if primary is unavailable)
LLM_FALLBACK_MODEL = None                     # Can configure a backup
```

### 6.3 Error Handling

```python
class LLMError(Exception):
    """Base LLM error."""

class LLMTimeoutError(LLMError):
    """LLM request timed out."""

class LLMRateLimitError(LLMError):
    """Provider rate limit hit."""

class LLMContentFilterError(LLMError):
    """Content filtered by provider."""


async def safe_llm_call(messages, **kwargs):
    """Wrapper with error classification and metrics."""
    try:
        return await llm_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            **kwargs,
        )
    except openai.APITimeoutError:
        metrics.llm_errors.labels(type="timeout").inc()
        raise LLMTimeoutError("LLM request timed out")
    except openai.RateLimitError:
        metrics.llm_errors.labels(type="rate_limit").inc()
        raise LLMRateLimitError("Provider rate limit exceeded")
    except openai.APIError as e:
        metrics.llm_errors.labels(type="api_error").inc()
        raise LLMError(f"LLM API error: {e}")
```

## 7. Evaluation & Quality Metrics

### 7.1 Automated Evaluation (Post-launch)

| Metric | Measurement | Target |
|--------|------------|--------|
| Citation accuracy | % of cited chunks actually relevant to the claim | >90% |
| Refusal appropriateness | Manual review of refusal samples | >85% correct |
| Answer groundedness | % of answer claims traceable to retrieved chunks | >95% |
| Retrieval precision@10 | % of top-10 chunks relevant to question | >60% |
| User satisfaction | Thumbs up/down ratio | >80% positive |

### 7.2 Logging for Evaluation

Every AI interaction is logged to analytics via Kafka:
```json
{
  "event_type": "AssistantQueryAsked",
  "payload": {
    "query_id": "uuid",
    "course_id": "uuid",
    "question_hash": "sha256",
    "chunks_retrieved": 8,
    "chunks_used_in_answer": 3,
    "max_relevance_score": 0.89,
    "avg_relevance_score": 0.72,
    "response_type": "answer",
    "confidence": "high",
    "tokens_used": {"input": 2000, "output": 400},
    "latency_ms": 1500,
    "cached": false
  }
}
```
