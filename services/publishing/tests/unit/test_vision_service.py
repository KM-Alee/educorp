from __future__ import annotations

import json

import pytest

from app.services.vision_service import _parse_vision_json


class TestParseVisionJson:
    def test_valid_json(self) -> None:
        raw = '{"factual_summary": "A diagram of a neural network.", "diagram_terms": ["weights", "activation"]}'
        result = _parse_vision_json(raw)
        assert result["factual_summary"] == "A diagram of a neural network."
        assert "weights" in result["diagram_terms"]

    def test_strips_markdown_fence(self) -> None:
        raw = '```json\n{"factual_summary": "slide text", "diagram_terms": []}\n```'
        result = _parse_vision_json(raw)
        assert result["factual_summary"] == "slide text"

    def test_empty_response(self) -> None:
        result = _parse_vision_json("")
        assert result == {}

    def test_invalid_json_returns_empty(self) -> None:
        result = _parse_vision_json("not json at all")
        assert result == {}

    def test_limits_diagram_terms_to_8(self) -> None:
        terms = [f"term{i}" for i in range(12)]
        raw = json.dumps({"factual_summary": "x", "diagram_terms": terms})
        result = _parse_vision_json(raw)
        assert len(result["diagram_terms"]) == 8

    def test_missing_keys_use_defaults(self) -> None:
        result = _parse_vision_json('{"factual_summary": "only summary"}')
        assert result["factual_summary"] == "only summary"
        assert result["diagram_terms"] == []
