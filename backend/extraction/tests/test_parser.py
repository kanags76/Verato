"""
Pure unit tests for extraction/parser.py — no DB, no network, no mocking.
"""
import json
import pytest
from extraction.parser import safe_json_parse


pytestmark = pytest.mark.unit

VALID_ITEM = {
    "raw_text": "I'll have the report ready by Friday.",
    "normalised_text": "Alice will deliver the report by Friday.",
    "commit_type": "explicit",
    "owner_name": "Alice",
    "deadline_text": "by Friday",
    "deadline_resolved": "2026-05-01",
    "confidence": 0.91,
}


class TestSafeJsonParseValid:
    def test_plain_json_array(self):
        result = safe_json_parse(json.dumps([VALID_ITEM]))
        assert len(result) == 1
        assert result[0]["owner_name"] == "Alice"
        assert result[0]["confidence"] == 0.91

    def test_empty_array_string(self):
        assert safe_json_parse("[]") == []

    def test_two_items(self):
        item2 = {**VALID_ITEM, "owner_name": "Bob", "confidence": 0.75}
        result = safe_json_parse(json.dumps([VALID_ITEM, item2]))
        assert len(result) == 2
        assert {r["owner_name"] for r in result} == {"Alice", "Bob"}

    def test_strips_json_fence(self):
        text = "```json\n" + json.dumps([VALID_ITEM]) + "\n```"
        result = safe_json_parse(text)
        assert len(result) == 1

    def test_strips_plain_fence(self):
        text = "```\n" + json.dumps([VALID_ITEM]) + "\n```"
        result = safe_json_parse(text)
        assert len(result) == 1

    def test_strips_fence_case_insensitive(self):
        text = "```JSON\n" + json.dumps([VALID_ITEM]) + "\n```"
        result = safe_json_parse(text)
        assert len(result) == 1

    def test_null_deadline_preserved(self):
        item = {**VALID_ITEM, "deadline_resolved": None}
        result = safe_json_parse(json.dumps([item]))
        assert result[0]["deadline_resolved"] is None


class TestSafeJsonParseDefaults:
    def test_missing_fields_get_defaults(self):
        minimal = {"raw_text": "I'll do it by Monday.", "confidence": 0.8}
        result = safe_json_parse(json.dumps([minimal]))
        assert len(result) == 1
        item = result[0]
        assert item["normalised_text"] == ""
        assert item["commit_type"] == "explicit"
        assert item["owner_name"] == ""
        assert item["deadline_text"] == ""
        assert item["deadline_resolved"] is None

    def test_confidence_clamped_above_one(self):
        item = {**VALID_ITEM, "confidence": 1.5}
        result = safe_json_parse(json.dumps([item]))
        assert result[0]["confidence"] == 1.0

    def test_confidence_clamped_below_zero(self):
        item = {**VALID_ITEM, "confidence": -0.3}
        result = safe_json_parse(json.dumps([item]))
        assert result[0]["confidence"] == 0.0

    def test_confidence_string_converted(self):
        item = {**VALID_ITEM, "confidence": "0.85"}
        result = safe_json_parse(json.dumps([item]))
        assert result[0]["confidence"] == pytest.approx(0.85)

    def test_confidence_invalid_string_defaults(self):
        item = {**VALID_ITEM, "confidence": "high"}
        result = safe_json_parse(json.dumps([item]))
        assert result[0]["confidence"] == 0.5


class TestSafeJsonParseInvalid:
    def test_empty_string_returns_empty(self):
        assert safe_json_parse("") == []

    def test_whitespace_only_returns_empty(self):
        assert safe_json_parse("   \n  ") == []

    def test_malformed_json_returns_empty(self):
        assert safe_json_parse("{not valid json}") == []

    def test_json_object_not_array_returns_empty(self):
        assert safe_json_parse(json.dumps({"key": "value"})) == []

    def test_json_string_not_array_returns_empty(self):
        assert safe_json_parse('"just a string"') == []

    def test_non_dict_items_skipped(self):
        mixed = json.dumps([VALID_ITEM, "a string", 42, VALID_ITEM])
        result = safe_json_parse(mixed)
        assert len(result) == 2

    def test_gemini_sorry_prefix_returns_empty(self):
        text = "I'm sorry, I cannot extract commitments from this text."
        assert safe_json_parse(text) == []

    def test_partial_json_returns_empty(self):
        assert safe_json_parse('[{"raw_text": "incomplete') == []
