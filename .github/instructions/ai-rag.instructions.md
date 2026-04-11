---
applyTo: "services/ai/app/**/*.py"
---

# AI/RAG Pipeline Conventions

## LLM Client
Use OpenAI-compatible client pointed at NanoGPT:
```python
from openai import AsyncOpenAI

llm = AsyncOpenAI(
    base_url=settings.llm_base_url,  # e.g., http://nanogpt:8080/v1
    api_key=settings.llm_api_key,
)
```

## Embedding
Use the same client for embeddings:
```python
response = await llm.embeddings.create(
    model=settings.embedding_model,
    input=[text],
)
embedding = response.data[0].embedding
```

## LangGraph State Machine
The Q&A pipeline is a LangGraph directed graph:
1. **validate** — Check input, verify enrollment
2. **retrieve** — Query Qdrant with course-scoped filter
3. **assess** — Evaluate chunk relevance (sufficient/insufficient/off_topic)
4. **generate** OR **refuse** OR **clarify** — Route based on assessment
5. **cite** — Extract and validate `[n]` references
6. **log** — Emit event to outbox

## Retrieval Rules
- Always filter by `course_id` AND `version_status = "READY"`
- Retrieve top 8 chunks, score threshold 0.7
- If < 2 chunks pass threshold → route to "refuse"
- Include chunk metadata (module, asset) in context for citation

## Generation Rules
- System prompt establishes the role and constraints
- Context includes numbered chunks: `[1] chunk_text (Module: X, Asset: Y)`
- Instruct LLM to cite with `[n]` notation
- Temperature: 0.3 for Q&A, 0.7 for instructor tools

## SSE Streaming
```python
from sse_starlette.sse import EventSourceResponse

async def event_generator():
    async for chunk in llm.chat.completions.create(..., stream=True):
        token = chunk.choices[0].delta.content
        if token:
            yield {"event": "token", "data": token}
    yield {"event": "citations", "data": json.dumps(citations)}
    yield {"event": "done", "data": ""}

return EventSourceResponse(event_generator())
```

## Safety
- Never allow cross-course content leakage
- Refuse off-topic questions with a polite message
- Rate limit: 20 req/min for students, 5 req/min for instructor tools
- Cache by: `hash(question) + course_id + version_id` → TTL 1 hour
- Log all queries and responses for quality monitoring

## Testing
- Mock LLM with `respx`:
```python
respx.post(f"{LLM_BASE_URL}/chat/completions").respond(
    json={"choices": [{"message": {"content": "Mocked answer [1]"}}]}
)
```
- Test refusal paths (irrelevant question, unenrolled user)
- Test citation extraction and validation
- Test streaming endpoint yields correct SSE events
