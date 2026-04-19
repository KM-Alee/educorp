from __future__ import annotations

import json
import time
from uuid import UUID, uuid4

import structlog
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
    'You are a course assistant for "{course_title}".\n'
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

HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.5
CLARIFY_MESSAGE = "Can you clarify what you want to know so I can find the right material?"


class QAStreamingService:
    """Streaming Q&A pipeline for SSE."""

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

    async def stream(
        self,
        *,
        course_id: UUID,
        question: str,
        module_id: UUID | None,
        user_id: UUID,
        role_scope: str,
    ):
        start_time = time.monotonic()
        query_id = uuid4()
        if role_scope != "admin":
            rate_limit = (
                settings.rate_limit_student_per_window
                if role_scope == "student"
                else settings.rate_limit_instructor_per_window
            )
            await self._rate_limiter.enforce(
                key=f"ratelimit:ai:{user_id}:{role_scope}",
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
            question=question,
            course_id=str(course_id),
            version_id=str(version_id),
        )
        if cached_response:
            answer = cached_response.get("answer", "")
            citations = cached_response.get("citations", [])
            for token in _tokenize(answer):
                yield {"event": "token", "data": json.dumps({"text": token})}
            for citation in citations:
                yield {"event": "citation", "data": json.dumps(citation)}
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "query_id": str(query_id),
                        "confidence": cached_response.get("confidence", "low"),
                        "total_citations": len(citations),
                    }
                ),
            }
            await self._emit_usage(
                query_id=query_id,
                user_id=user_id,
                course_id=course_id,
                version_id=UUID(str(version_id)),
                question_text=question,
                chunks=0,
                response_status="answered",
                citations=len(citations),
                latency_ms=int((time.monotonic() - start_time) * 1000),
                tokens_used=cached_response.get("tokens_used", {"input": 0, "output": 0}),
                cached=True,
            )
            return

        chunks, scores = await self._retriever.retrieve(
            course_id=course_id,
            version_id=UUID(str(version_id)),
            question=question,
            module_id=module_id,
        )

        if len(chunks) < settings.min_chunks_for_answer:
            await self._emit_refusal(
                query_id=query_id,
                user_id=user_id,
                course_id=course_id,
                version_id=UUID(str(version_id)),
                question=question,
                chunks=len(chunks),
                start_time=start_time,
            )
            yield {"event": "token", "data": json.dumps({"text": REFUSAL_MESSAGE})}
            yield {
                "event": "done",
                "data": json.dumps(
                    {"query_id": str(query_id), "confidence": "low", "total_citations": 0}
                ),
            }
            return

        top_score = max(scores) if scores else 0
        if top_score < settings.relevance_threshold:
            await self._emit_refusal(
                query_id=query_id,
                user_id=user_id,
                course_id=course_id,
                version_id=UUID(str(version_id)),
                question=question,
                chunks=len(chunks),
                start_time=start_time,
            )
            yield {"event": "token", "data": json.dumps({"text": REFUSAL_MESSAGE})}
            yield {
                "event": "done",
                "data": json.dumps(
                    {"query_id": str(query_id), "confidence": "low", "total_citations": 0}
                ),
            }
            return

        avg_score = sum(scores) / len(scores) if scores else 0
        top_gap = (scores[0] - scores[1]) if len(scores) > 1 else scores[0] if scores else 0.0
        confidence = (
            "high"
            if avg_score >= HIGH_CONFIDENCE_THRESHOLD
            else "medium"
            if avg_score >= MEDIUM_CONFIDENCE_THRESHOLD
            else "low"
        )

        is_ambiguous = bool(
            module_id is None
            and len(chunks) >= 2
            and top_gap < 0.08
            and avg_score < HIGH_CONFIDENCE_THRESHOLD
        )
        if is_ambiguous:
            await self._store_clarification_context(
                query_id=query_id,
                course_id=course_id,
                user_id=user_id,
                question=question,
                module_id=module_id,
            )
            await self._emit_usage(
                query_id=query_id,
                user_id=user_id,
                course_id=course_id,
                version_id=UUID(str(version_id)),
                question_text=question,
                chunks=len(chunks),
                response_status="clarification_requested",
                citations=0,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                tokens_used={"input": 0, "output": 0},
                cached=False,
            )
            yield {"event": "clarification", "data": json.dumps({"message": CLARIFY_MESSAGE})}
            yield {
                "event": "done",
                "data": json.dumps(
                    {"query_id": str(query_id), "confidence": "low", "total_citations": 0}
                ),
            }
            return

        formatted = "\n\n".join(
            _format_chunk(i + 1, chunk)
            for i, chunk in enumerate(chunks[: settings.max_context_chunks])
        )
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(course_title=course_title or ""),
            },
            {
                "role": "user",
                "content": CONTEXT_TEMPLATE.format(
                    formatted_chunks=formatted,
                    question=question,
                ),
            },
        ]

        answer = ""
        async for token in self._llm.chat_completion_stream(
            messages=messages,
            temperature=0.3,
            max_tokens=settings.max_output_tokens,
        ):
            answer += token
            yield {"event": "token", "data": json.dumps({"text": token})}

        citations = build_citations(answer, chunks)
        if invalid_citation_refs(answer, len(chunks)):
            await self._emit_refusal(
                query_id=query_id,
                user_id=user_id,
                course_id=course_id,
                version_id=UUID(str(version_id)),
                question=question,
                chunks=len(chunks),
                start_time=start_time,
            )
            yield {"event": "refusal", "data": json.dumps({"message": REFUSAL_MESSAGE})}
            yield {
                "event": "done",
                "data": json.dumps(
                    {"query_id": str(query_id), "confidence": "low", "total_citations": 0}
                ),
            }
            return
        for citation in citations:
            yield {"event": "citation", "data": json.dumps(citation)}

        await set_cached_response(
            self._redis,
            question=question,
            course_id=str(course_id),
            version_id=str(version_id),
            payload={
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "response_type": "answer",
                "tokens_used": {"input": 0, "output": 0},
            },
        )

        await self._emit_usage(
            query_id=query_id,
            user_id=user_id,
            course_id=course_id,
            version_id=UUID(str(version_id)),
            question_text=question,
            chunks=len(chunks),
            response_status="answered",
            citations=len(citations),
            latency_ms=int((time.monotonic() - start_time) * 1000),
            tokens_used={"input": 0, "output": 0},
            cached=False,
        )

        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "query_id": str(query_id),
                    "confidence": confidence,
                    "total_citations": len(citations),
                }
            ),
        }

    async def _emit_refusal(
        self,
        *,
        query_id: UUID,
        user_id: UUID,
        course_id: UUID,
        version_id: UUID,
        question: str,
        chunks: int,
        start_time: float,
    ) -> None:
        await self._emit_usage(
            query_id=query_id,
            user_id=user_id,
            course_id=course_id,
            version_id=version_id,
            question_text=question,
            chunks=chunks,
            response_status="refused",
            citations=0,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            tokens_used={"input": 0, "output": 0},
            cached=False,
        )

    async def _emit_usage(
        self,
        *,
        query_id: UUID,
        user_id: UUID,
        course_id: UUID,
        version_id: UUID,
        question_text: str,
        chunks: int,
        response_status: str,
        citations: int,
        latency_ms: int,
        tokens_used: dict[str, int],
        cached: bool,
    ) -> None:
        payload = build_assistant_query_payload(
            query_id=query_id,
            student_id=user_id,
            course_id=course_id,
            version_id=version_id,
            question_text=question_text,
            chunks_retrieved=chunks,
            response_status=response_status,
            citations_count=citations,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cached=cached,
        )
        event_query = build_event(
            event_type="AssistantQueryAsked",
            aggregate_type="ai_query",
            aggregate_id=str(query_id),
            actor_id=str(user_id),
            payload=payload,
        )
        await emit_event(self._kafka_producer, event_query)
        event = build_event(
            event_type="AssistantAnswerGenerated",
            aggregate_type="ai_query",
            aggregate_id=str(query_id),
            actor_id=str(user_id),
            payload=payload,
        )
        await emit_event(self._kafka_producer, event)

    async def _store_clarification_context(
        self,
        *,
        query_id: UUID,
        course_id: UUID,
        user_id: UUID,
        question: str,
        module_id: UUID | None,
    ) -> None:
        await self._redis.setex(
            f"clarify:ai:{query_id}",
            settings.clarify_context_ttl_seconds,
            json.dumps(
                {
                    "course_id": str(course_id),
                    "user_id": str(user_id),
                    "question": question,
                    "module_id": None if module_id is None else str(module_id),
                }
            ),
        )


def _format_chunk(index: int, chunk: dict) -> str:
    module_title = chunk.get("module_title") or ""
    asset_title = chunk.get("asset_title") or ""
    page = chunk.get("page_number")
    page_label = f", Page {page}" if page is not None else ""
    text = chunk.get("text", "")
    return f"[{index}] (Module: {module_title}, Asset: {asset_title}{page_label})\n{text}"


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    tokens = text.split()
    return [f"{token} " for token in tokens]
