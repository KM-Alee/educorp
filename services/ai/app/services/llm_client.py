from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.config import settings
from educorp_common.errors import EduCorpError


@dataclass(frozen=True)
class LLMResult:
    content: str
    usage: dict[str, int]


class LLMClient:
    """OpenAI-compatible client wrapper for chat completions."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResult:
        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except RateLimitError as exc:
            raise EduCorpError(
                code="RATE_LIMIT_EXCEEDED",
                message="LLM provider rate limit exceeded",
                status_code=429,
            ) from exc
        except APITimeoutError as exc:
            raise EduCorpError(
                code="AI_TIMEOUT",
                message="LLM provider request timed out",
                status_code=502,
            ) from exc
        except (APIConnectionError, APIError) as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="LLM provider error",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Unexpected LLM provider error",
                status_code=502,
            ) from exc

        content = response.choices[0].message.content or ""
        usage = _usage_to_dict(response.usage)
        return LLMResult(content=content, usage=usage)

    async def chat_completion_stream(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield text
        except RateLimitError as exc:
            raise EduCorpError(
                code="RATE_LIMIT_EXCEEDED",
                message="LLM provider rate limit exceeded",
                status_code=429,
            ) from exc
        except APITimeoutError as exc:
            raise EduCorpError(
                code="AI_TIMEOUT",
                message="LLM provider request timed out",
                status_code=502,
            ) from exc
        except (APIConnectionError, APIError) as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="LLM provider error",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise EduCorpError(
                code="AI_PROVIDER_ERROR",
                message="Unexpected LLM provider error",
                status_code=502,
            ) from exc


def _usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"input": 0, "output": 0}
    return {
        "input": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output": int(getattr(usage, "completion_tokens", 0) or 0),
    }
