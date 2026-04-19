from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.ai_jobs_repository import AiJobsRepository
from app.repositories.entitlement_repository import EntitlementRepository
from app.services.citation_service import build_citations
from app.services.embedding_client import EmbeddingClient
from app.services.event_emitter import build_assistant_query_payload, build_event, emit_event
from app.services.llm_client import LLMClient
from app.services.rate_limiter import RateLimiter
from app.services.retriever import QdrantRetriever
from app.services.token_utils import estimate_tokens, truncate_to_token_limit
from educorp_common.errors import EduCorpError, ForbiddenError

logger = structlog.get_logger()

INSTRUCTOR_PROMPTS: dict[str, dict[str, str]] = {
    "summary": {
        "system": (
            "You are an educational content expert. Generate a clear, structured summary "
            "of the course material. The summary should: "
            "- Highlight key concepts and relationships "
            "- Be appropriate for {difficulty} level learners "
            "- Stay under {max_length} words "
            "- Reference excerpts using [n] citations"
        ),
        "user": "Course material:\n\n{context}\n\nGenerate a summary.",
    },
    "objectives": {
        "system": (
            "You are an instructional designer. Generate learning objectives using "
            "Bloom's taxonomy. Each objective should: "
            "- Start with an action verb "
            "- Be measurable and specific "
            "- Cover key topics "
            "- Reference excerpts using [n] citations"
        ),
        "user": "Course material:\n\n{context}\n\nGenerate 5-10 learning objectives.",
    },
    "quiz": {
        "system": (
            "You are an assessment expert. Generate quiz questions from the course material. "
            "Requirements: "
            "- {question_count} questions "
            "- Mix of multiple choice and short answer "
            "- Each question must have a correct answer and explanation "
            "- Each answer must reference excerpts using [n] citations"
        ),
        "user": "Course material:\n\n{context}\n\nGenerate quiz questions.",
    },
    "glossary": {
        "system": (
            "You are a subject matter expert. Extract key terms and provide clear, concise "
            "definitions based on the course material. Each entry should: "
            "- Be understandable at {difficulty} level "
            "- Reference excerpts using [n] citations"
        ),
        "user": "Course material:\n\n{context}\n\nGenerate a glossary.",
    },
}


class InstructorService:
    """Instructor enhancement jobs and streaming generation."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        redis: Redis,
        qdrant,
        mongo_db,
        kafka_producer,
    ) -> None:
        self._repo = EntitlementRepository(session)
        self._jobs = AiJobsRepository(mongo_db)
        self._redis = redis
        self._rate_limiter = RateLimiter(redis)
        self._retriever = QdrantRetriever(qdrant, EmbeddingClient())
        self._llm = LLMClient()
        self._kafka_producer = kafka_producer

    async def enqueue_job(
        self,
        *,
        job_id: UUID,
        job_type: str,
        course_id: UUID,
        module_id: UUID | None,
        scope: str,
        parameters: dict[str, Any],
        requested_by: UUID,
        roles: list[str] | None = None,
    ) -> None:
        if scope == "module" and module_id is None:
            raise EduCorpError(
                code="MODULE_SCOPE_REQUIRES_MODULE_ID",
                message="module_id is required when scope is module",
                status_code=422,
            )
        version_id, _ = await self._repo.get_ready_course_version(course_id)
        if version_id is None:
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not ready for AI enhancement",
                status_code=409,
            )

        await self._require_owner(course_id, requested_by, roles)

        await self._jobs.create_job(
            {
                "job_id": str(job_id),
                "job_type": job_type,
                "course_id": str(course_id),
                "version_id": str(version_id),
                "requested_by": str(requested_by),
                "status": "QUEUED",
                "input": {
                    "scope": scope,
                    "module_id": str(module_id) if module_id else None,
                    "parameters": parameters,
                },
            }
        )

        asyncio.create_task(
            self._process_job(
                job_id=job_id,
                job_type=job_type,
                course_id=course_id,
                module_id=module_id,
                scope=scope,
                parameters=parameters,
                requested_by=requested_by,
                version_id=version_id,
            )
        )

    async def stream_job(
        self,
        *,
        job_id: UUID,
        job_type: str,
        course_id: UUID,
        module_id: UUID | None,
        scope: str,
        parameters: dict[str, Any],
        requested_by: UUID,
        roles: list[str] | None = None,
    ):
        if scope == "module" and module_id is None:
            raise EduCorpError(
                code="MODULE_SCOPE_REQUIRES_MODULE_ID",
                message="module_id is required when scope is module",
                status_code=422,
            )
        version_id, _ = await self._repo.get_ready_course_version(course_id)
        if version_id is None:
            raise EduCorpError(
                code="COURSE_NOT_READY",
                message="Course is not ready for AI enhancement",
                status_code=409,
            )

        await self._require_owner(course_id, requested_by, roles)

        await self._rate_limiter.enforce(
            key=f"ratelimit:ai:{requested_by}:instructor",
            limit=settings.rate_limit_instructor_per_window,
            window_seconds=settings.rate_limit_window_seconds,
        )

        await self._jobs.create_job(
            {
                "job_id": str(job_id),
                "job_type": job_type,
                "course_id": str(course_id),
                "version_id": str(version_id),
                "requested_by": str(requested_by),
                "status": "RUNNING",
                "started_at": datetime.now(timezone.utc),
                "input": {
                    "scope": scope,
                    "module_id": str(module_id) if module_id else None,
                    "parameters": parameters,
                },
            }
        )

        try:
            chunks, _ = await self._retriever.retrieve(
                course_id=course_id,
                version_id=version_id,
                question=_stream_query_hint(job_type, parameters, module_id),
                module_id=module_id if scope == "module" else None,
            )
            await self._ensure_not_cancelled(job_id)
            context = _build_context(chunks)
            if estimate_tokens(context) > settings.max_input_tokens:
                context = truncate_to_token_limit(context, settings.max_input_tokens)

            prompt = INSTRUCTOR_PROMPTS[job_type]
            messages = [
                {
                    "role": "system",
                    "content": prompt["system"].format(
                        difficulty=parameters.get("difficulty", "intermediate"),
                        max_length=parameters.get("max_length", 500),
                        question_count=parameters.get("question_count", 10),
                    ),
                },
                {"role": "user", "content": prompt["user"].format(context=context)},
            ]

            answer = ""
            async for token in self._llm.chat_completion_stream(
                messages=messages,
                temperature=0.7,
                max_tokens=settings.max_output_tokens,
            ):
                answer += token
                yield {"event": "token", "data": _json({"text": token})}

            citations = build_citations(answer, chunks)
            for citation in citations:
                yield {"event": "citation", "data": _json(citation)}

            await self._ensure_not_cancelled(job_id)
            await self._jobs.update_job(
                str(job_id),
                {
                    "status": "COMPLETED",
                    "completed_at": datetime.now(timezone.utc),
                    "result": _result_payload(
                        job_type, answer, citations, {"input": 0, "output": 0}
                    ),
                },
            )

            await self._emit_usage(
                query_id=job_id,
                user_id=requested_by,
                course_id=course_id,
                version_id=version_id,
                question_text=f"instructor:{job_type}",
                chunks=len(chunks),
                response_status="answered",
                citations=len(citations),
                latency_ms=0,
                tokens_used={"input": 0, "output": 0},
                cached=False,
            )

            yield {
                "event": "done",
                "data": _json({"job_id": str(job_id), "total_citations": len(citations)}),
            }
        except Exception as exc:
            logger.warning("Instructor streaming failed", exc_info=exc)
            await self._mark_failed(job_id, exc)
            raise

    async def cancel_job(self, job_id: UUID) -> None:
        await self._jobs.update_job(
            str(job_id),
            {"status": "CANCELLED", "completed_at": datetime.now(timezone.utc)},
        )

    async def _process_job(
        self,
        *,
        job_id: UUID,
        job_type: str,
        course_id: UUID,
        module_id: UUID | None,
        scope: str,
        parameters: dict[str, Any],
        requested_by: UUID,
        version_id: UUID,
    ) -> None:
        try:
            await self._rate_limiter.enforce(
                key=f"ratelimit:ai:{requested_by}:instructor",
                limit=settings.rate_limit_instructor_per_window,
                window_seconds=settings.rate_limit_window_seconds,
            )

            await self._jobs.update_job(
                str(job_id),
                {"status": "RUNNING", "started_at": datetime.now(timezone.utc)},
            )

            chunks, _ = await self._retriever.retrieve(
                course_id=course_id,
                version_id=version_id,
                question=_stream_query_hint(job_type, parameters, module_id),
                module_id=module_id if scope == "module" else None,
            )
            await self._ensure_not_cancelled(job_id)
            context = _build_context(chunks)
            if estimate_tokens(context) > settings.max_input_tokens:
                context = truncate_to_token_limit(context, settings.max_input_tokens)

            prompt = INSTRUCTOR_PROMPTS[job_type]
            messages = [
                {
                    "role": "system",
                    "content": prompt["system"].format(
                        difficulty=parameters.get("difficulty", "intermediate"),
                        max_length=parameters.get("max_length", 500),
                        question_count=parameters.get("question_count", 10),
                    ),
                },
                {"role": "user", "content": prompt["user"].format(context=context)},
            ]

            result = await self._llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=settings.max_output_tokens,
            )
            citations = build_citations(result.content, chunks)
            await self._ensure_not_cancelled(job_id)
            await self._jobs.update_job(
                str(job_id),
                {
                    "status": "COMPLETED",
                    "completed_at": datetime.now(timezone.utc),
                    "result": _result_payload(job_type, result.content, citations, result.usage),
                },
            )

            await self._emit_usage(
                query_id=job_id,
                user_id=requested_by,
                course_id=course_id,
                version_id=version_id,
                question_text=f"instructor:{job_type}",
                chunks=len(chunks),
                response_status="answered",
                citations=len(citations),
                latency_ms=0,
                tokens_used=result.usage,
                cached=False,
            )
        except Exception as exc:
            logger.warning("Instructor job failed", exc_info=exc)
            await self._mark_failed(job_id, exc)

    async def _require_owner(
        self,
        course_id: UUID,
        user_id: UUID,
        roles: list[str] | None = None,
    ) -> None:
        if roles and "admin" in roles:
            return
        is_owner = await self._repo.is_course_owner(user_id, course_id)
        if not is_owner:
            raise ForbiddenError("Only the course owner can use instructor tools")

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
        event = build_event(
            event_type="AssistantAnswerGenerated",
            aggregate_type="ai_job",
            aggregate_id=str(query_id),
            actor_id=str(user_id),
            payload=payload,
        )
        await emit_event(self._kafka_producer, event)

    async def reconcile_orphaned_jobs(self) -> None:
        await self._jobs.mark_incomplete_jobs_failed()

    async def _ensure_not_cancelled(self, job_id: UUID) -> None:
        current = await self._jobs.get_job(str(job_id))
        if current and current.get("status") == "CANCELLED":
            raise EduCorpError(
                code="JOB_CANCELLED",
                message="Job was cancelled",
                status_code=409,
            )

    async def _mark_failed(self, job_id: UUID, exc: Exception) -> None:
        current = await self._jobs.get_job(str(job_id))
        if current and current.get("status") == "CANCELLED":
            return
        await self._jobs.update_job(
            str(job_id),
            {
                "status": "FAILED",
                "completed_at": datetime.now(timezone.utc),
                "error": {
                    "code": getattr(exc, "code", "AI_PROVIDER_ERROR"),
                    "message": str(exc),
                    "retryable": False,
                },
            },
        )


def _build_context(chunks: list[dict]) -> str:
    lines = []
    for i, chunk in enumerate(chunks[: settings.max_context_chunks]):
        lines.append(
            f"[{i + 1}] (Module: {chunk.get('module_title')}, Asset: {chunk.get('asset_title')})\n"
            f"{chunk.get('text', '')}"
        )
    return "\n\n".join(lines)


def _stream_query_hint(job_type: str, parameters: dict[str, Any], module_id: UUID | None) -> str:
    if module_id is not None:
        return f"module {module_id}"
    hint = job_type
    if job_type == "quiz":
        hint = f"quiz {parameters.get('question_count', 10)} questions"
    return hint


def _result_payload(
    job_type: str,
    content: str,
    citations: list[dict[str, Any]],
    tokens_used: dict[str, int],
) -> dict[str, Any]:
    return {
        "type": job_type,
        "content": content,
        "citations": citations,
        "tokens_used": tokens_used,
    }


def _json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload)
