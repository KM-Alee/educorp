from __future__ import annotations

import base64
import json
import logging
import re

from app.config import settings
from educorp_common.inter_service_http import inter_service_request

logger = logging.getLogger(__name__)

_PROMPT = (
    "You are analyzing a lecture slide or diagram image. "
    "Respond with valid JSON only — no markdown fences, no commentary. "
    'Schema: {"factual_summary": "<one factual sentence>", "diagram_terms": ["term1", "term2"]}. '
    "Do not paraphrase or rewrite lecture content. "
    "Limit diagram_terms to at most 8 unique technical terms visible in the image."
)


class VisionService:
    """NanoGPT visual enrichment adapter for image-heavy PDF pages."""

    def __init__(self) -> None:
        self._base_url = settings.nanogpt_base_url.rstrip("/")
        self._api_key = settings.nanogpt_api_key
        self._model = settings.nanogpt_model

    async def enrich_page(self, png_bytes: bytes) -> dict[str, object]:
        """
        Send a rendered page PNG to NanoGPT and return structured vision fields.

        Returns a dict with keys ``factual_summary`` (str) and ``diagram_terms`` (list[str]).
        Returns an empty dict on any provider error without raising.
        """
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ]
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key and self._api_key != "change-me":
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await inter_service_request(
                "POST",
                f"{self._base_url}/chat/completions",
                timeout=90.0,
                headers=headers,
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.1,
                },
            )
        except Exception as exc:
            logger.warning("NanoGPT vision request error: %s", exc)
            return {}

        if response.is_error:
            logger.warning(
                "NanoGPT vision enrichment HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
            return {}

        payload = response.json()
        raw_content: str = (
            payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        return _parse_vision_json(raw_content)


def _parse_vision_json(raw: str) -> dict[str, object]:
    """Parse JSON response from NanoGPT, tolerating markdown fences."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
        return {
            "factual_summary": str(result.get("factual_summary", "")),
            "diagram_terms": [str(t) for t in result.get("diagram_terms", [])[:8]],
        }
    except json.JSONDecodeError:
        logger.debug("Could not parse vision response as JSON: %r", raw[:300])
        return {}
