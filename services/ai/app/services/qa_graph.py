from __future__ import annotations

import time
from typing import TypedDict
from uuid import UUID, uuid4

import structlog
from langgraph.graph import END, StateGraph
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.entitlement_repository import EntitlementRepository
from app.services.cache import get_cached_response, set_cached_response
from app.services.citation_service import build_citations, invalid_citation_refs
from app.services.embedding_client import EmbeddingClient
from app.services.event_emitter import build_assistant_query_payload, build_event, emit_event
from app.services.llm_client import LLMClient
from app.services.rate_limiter import RateLimiter
from app.services.retriever import QdrantRetriever
from educorp_common.errors import EduCorpError, ForbiddenError

logger = structlog.get_logger()

SYSTEM_PROMPT = (
    "You are a course assistant for \"{course_title}\".\n"
    "Your job is to answer the student's question using ONLY the provided course material excerpts.\n\n"
    "RULES:\n"
    "1. ONLY use information from the provided excerpts. Never use external knowledge.\n"
    "2. If the excerpts do not contain enough information, say so clearly.\n"
    "3. For each claim you make, reference the source excerpt by its [number].\n"
    "4. Be concise and educational.\n"
    "5. If the question is about something not covered in the course, politely decline.\n"
    "6. Never make up information. Never hallucinate citations."
)

CONTEXT_TEMPLATE = (
    "Here are relevant excerpts from the course material:\n\n{formatted_chunks}\n\n"
    "---\nStudent's question: {question}"
)

REFUSAL_MESSAGE = (
    "I do not have enough information from the course materials to answer that question."
)

CLARIFY_MESSAGE = "Can you clarify what you want to know so I can find the right material?"

HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.5


class QAState(TypedDict, total=False):
    # Input
    course_id: UUID
    question: str
    module_id: UUID | None
    user_id: UUID
    role_scope: str

    # Metadata
    query_id: UUID
    version_id: UUID
    course_title: str | None
    start_time: float
    cached: bool

    # Retrieval
    chunks: list[dict]
    relevance_scores: list[float]

    # Assessment
    has_sufficient_context: bool
    is_ambiguous: bool
    confidence: str

    # Output
    answer: str
    citations: list[dict]
    response_type: str
    tokens_used: dict[str, int]


class QAService:
    """LangGraph-backed Q&A pipeline."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        redis: Redis,
        qdrant,
        kafka_producer,
    ) -> None:
        self._repo = EntitlementRepository(session)
        self._redis = redis
        self._rate_limiter = RateLimiter(redis)
        self._retriever = QdrantRetriever(qdrant, EmbeddingClient())
        self._llm = LLMClient()
        self._kafka_producer = kafka_producer
        self._graph = build_qa_graph(self)

    async def ask(
        self,
        *,
        course_id: UUID,
        question: str,
        module_id: UUID | None,
        user_id: UUID,
        role_scope: str,
    ) -> QAState:
        state: QAState = {
            "course_id": course_id,
            "question": question,
            "module_id": module_id,
            "user_id": user_id,
            "role_scope": role_scope,
            "query_id": uuid4(),
            "start_time": time.monotonic(),
            "cached": False,
        }
        return await self._graph.ainvoke(state)

    async def _validate(self, state: QAState) -> QAState:
        course_id = state["course_id"]
        user_id = state["user_id"]
        role_scope = state["role_scope"]

        rate_limit = (
            settings.rate_limit_student_per_window
            if role_scope == "student"
            else settings.rate_limit_instructor_per_window
        )
        rate_key = f"ratelimit:ai:{user_id}:{role_scope}"
        await self._rate_limiter.enforce(
            key=rate_key,
            limit=rate_limit,
            window_seconds=settings.rate_limit_window_seconds,
        )

        version_id, course_title = await self._repo.get_ready_course_version(course_id)
        if version_id is None:
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not ready for AI assistance",
                status_code=409,
            )

        cache_key = f"cache:enrolled:{user_id}:{course_id}"
        cached = await self._redis.get(cache_key)
        if cached is None:
            enrolled = await self._repo.is_enrolled(user_id, course_id)
            await self._redis.setex(
                cache_key,
                settings.enrollment_cache_ttl_seconds,
                "1" if enrolled else "0",
            )
        else:
            enrolled = cached == "1"

        if not enrolled and role_scope == "student":
            raise ForbiddenError("Enrollment required for AI assistance")

        cached_response = await get_cached_response(
            self._redis,
            question=state["question"],
            course_id=str(course_id),
            version_id=str(version_id),
        )
        if cached_response:
            state.update(
                {
                    "cached": True,
                    "answer": cached_response.get("answer", ""),
                    "citations": cached_response.get("citations", []),
                    "confidence": cached_response.get("confidence", "low"),
                    "response_type": cached_response.get("response_type", "answer"),
                    "tokens_used": cached_response.get("tokens_used", {"input": 0, "output": 0}),
                }
            )

        state["version_id"] = UUID(str(version_id))
        state["course_title"] = course_title
        return state

    async def _retrieve(self, state: QAState) -> QAState:
        chunks, scores = await self._retriever.retrieve(
            course_id=state["course_id"],
            question=state["question"],
            module_id=state.get("module_id"),
        )
        return {"chunks": chunks, "relevance_scores": scores}

    async def _assess(self, state: QAState) -> QAState:
        chunks = state.get("chunks", [])
        scores = state.get("relevance_scores", [])

        if len(chunks) < settings.min_chunks_for_answer:
            return {"has_sufficient_context": False, "is_ambiguous": False}

        top_score = max(scores) if scores else 0
        if top_score < settings.relevance_threshold:
            return {"has_sufficient_context": False, "is_ambiguous": False}

        avg_score = sum(scores) / len(scores) if scores else 0
        confidence = (
            "high"
            if avg_score >= HIGH_CONFIDENCE_THRESHOLD
            else "medium"
            if avg_score >= MEDIUM_CONFIDENCE_THRESHOLD
            else "low"
        )

        return {
            "has_sufficient_context": True,
            "is_ambiguous": False,
            "confidence": confidence,
        }

    async def _generate(self, state: QAState) -> QAState:
        chunks = state.get("chunks", [])[: settings.max_context_chunks]
        formatted = "\n\n".join(
            _format_chunk(i + 1, chunk) for i, chunk in enumerate(chunks)
        )
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(course_title=state.get("course_title") or ""),
            },
            {
                "role": "user",
                "content": CONTEXT_TEMPLATE.format(
                    formatted_chunks=formatted,
                    question=state["question"],
                ),
            },
        ]

        result = await self._llm.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=settings.max_output_tokens,
        )
        return {
            "answer": result.content,
            "tokens_used": result.usage,
            "response_type": "answer",
        }

    async def _refuse(self, state: QAState) -> QAState:
        return {
            "answer": REFUSAL_MESSAGE,
            "citations": [],
            "confidence": "low",
            "response_type": "refusal",
            "tokens_used": {"input": 0, "output": 0},
        }

    async def _clarify(self, state: QAState) -> QAState:
        return {
            "answer": CLARIFY_MESSAGE,
            "citations": [],
            "confidence": "low",
            "response_type": "clarification",
            "tokens_used": {"input": 0, "output": 0},
        }

    async def _build_citations(self, state: QAState) -> QAState:
        citations = build_citations(state.get("answer", ""), state.get("chunks", []))
        invalid_refs = invalid_citation_refs(state.get("answer", ""), len(state.get("chunks", [])))
        if invalid_refs:
            logger.warning("Invalid citation references", invalid_refs=invalid_refs)
        return {"citations": citations}

    async def _log_and_emit(self, state: QAState) -> QAState:
        latency_ms = int((time.monotonic() - state["start_time"]) * 1000)
        citations = state.get("citations", [])
        response_type = state.get("response_type", "answer")
        response_status = _response_status(response_type)

        payload = build_assistant_query_payload(
            query_id=state["query_id"],
            student_id=state["user_id"],
            course_id=state["course_id"],
            version_id=state["version_id"],
            question_text=state["question"],
            chunks_retrieved=len(state.get("chunks", [])),
            response_status=response_status,
            citations_count=len(citations),
            latency_ms=latency_ms,
            tokens_used=state.get("tokens_used", {"input": 0, "output": 0}),
            cached=state.get("cached", False),
        )

        event_base = build_event(
            event_type="AssistantQueryAsked",
            aggregate_type="ai_query",
            aggregate_id=str(state["query_id"]),
            actor_id=str(state["user_id"]),
            payload=payload,
        )
        await emit_event(self._kafka_producer, event_base)

        event_answer = build_event(
            event_type="AssistantAnswerGenerated",
            aggregate_type="ai_query",
            aggregate_id=str(state["query_id"]),
            actor_id=str(state["user_id"]),
            payload=payload,
        )
        await emit_event(self._kafka_producer, event_answer)

        if response_type == "answer" and not state.get("cached", False):
            await set_cached_response(
                self._redis,
                question=state["question"],
                course_id=str(state["course_id"]),
                version_id=str(state["version_id"]),
                payload={
                    "answer": state.get("answer", ""),
                    "citations": citations,
                    "confidence": state.get("confidence", "low"),
                    "response_type": response_type,
                    "tokens_used": state.get("tokens_used", {"input": 0, "output": 0}),
                },
            )

        return state


def build_qa_graph(service: QAService):
    graph = StateGraph(QAState)

    graph.add_node("validate", service._validate)
    graph.add_node("retrieve", service._retrieve)
    graph.add_node("assess", service._assess)
    graph.add_node("generate", service._generate)
    graph.add_node("refuse", service._refuse)
    graph.add_node("clarify", service._clarify)
    graph.add_node("build_citations", service._build_citations)
    graph.add_node("log_and_emit", service._log_and_emit)

    graph.set_entry_point("validate")

    graph.add_conditional_edges("validate", _route_after_validate, {
        "cached": "log_and_emit",
        "retrieve": "retrieve",
    })
    graph.add_edge("retrieve", "assess")
    graph.add_conditional_edges("assess", _route_after_assess, {
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


def _route_after_validate(state: QAState) -> str:
    if state.get("cached"):
        return "cached"
    return "retrieve"


def _route_after_assess(state: QAState) -> str:
    if not state.get("has_sufficient_context"):
        return "refuse"
    if state.get("is_ambiguous"):
        return "clarify"
    return "generate"


def _response_status(response_type: str) -> str:
    if response_type == "refusal":
        return "refused"
    if response_type == "clarification":
        return "refused"
    return "answered"


def _format_chunk(index: int, chunk: dict) -> str:
    module_title = chunk.get("module_title") or ""
    asset_title = chunk.get("asset_title") or ""
    page = chunk.get("page_number")
    page_label = f", Page {page}" if page is not None else ""
    text = chunk.get("text", "")
    return f"[{index}] (Module: {module_title}, Asset: {asset_title}{page_label})\n{text}"
