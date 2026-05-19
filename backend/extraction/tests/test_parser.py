"""
Pure unit tests for extraction/parser.py — no DB, no network, no mocking.
"""
import json
import pytest
from extraction.parser import safe_json_parse, parse_extraction_response


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


# ---------------------------------------------------------------------------
# Tests for parse_extraction_response() — Week 3.5 extended format
# ---------------------------------------------------------------------------

VALID_EXTENDED = {
    "commitments": [
        {
            "raw_text": "I'll have the report ready by Friday.",
            "normalised_text": "Alice will deliver the report by Friday.",
            "commit_type": "explicit",
            "owner_name": "Alice",
            "deadline_text": "by Friday",
            "deadline_resolved": "2026-05-01",
            "confidence": 0.91,
            "tags": ["report delivery"],
        }
    ],
    "meeting_topics": [
        {"label": "report delivery", "confidence": 0.95},
        {"label": "q2 planning",     "confidence": 0.88},
    ],
    "meeting_type": "leadership",
    "meeting_summary": "Team discussed Q2 planning and report delivery.",
}


@pytest.mark.unit
class TestParseExtractionResponse:

    # --- Valid new format ---

    def test_returns_dict_with_four_keys(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert set(result.keys()) == {"commitments", "topics", "meeting_type", "summary"}

    def test_commitments_extracted(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert len(result["commitments"]) == 1
        assert result["commitments"][0]["owner_name"] == "Alice"

    def test_commitment_tags_populated(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert result["commitments"][0]["tags"] == ["report delivery"]

    def test_topics_extracted_and_filtered(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert len(result["topics"]) == 2
        labels = [t["label"] for t in result["topics"]]
        assert "report delivery" in labels

    def test_topic_below_threshold_excluded(self):
        data = {**VALID_EXTENDED, "meeting_topics": [
            {"label": "main topic", "confidence": 0.80},
            {"label": "weak topic", "confidence": 0.50},  # below 0.60 threshold
        ]}
        result = parse_extraction_response(json.dumps(data))
        labels = [t["label"] for t in result["topics"]]
        assert "main topic" in labels
        assert "weak topic" not in labels

    def test_meeting_type_returned(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert result["meeting_type"] == "leadership"

    def test_summary_returned(self):
        result = parse_extraction_response(json.dumps(VALID_EXTENDED))
        assert result["summary"] == "Team discussed Q2 planning and report delivery."

    def test_fenced_json_still_works(self):
        fenced = "```json\n" + json.dumps(VALID_EXTENDED) + "\n```"
        result = parse_extraction_response(fenced)
        assert len(result["commitments"]) == 1

    # --- Graceful fallbacks — never fail the pipeline ---

    def test_missing_topics_defaults_empty(self):
        data = {k: v for k, v in VALID_EXTENDED.items() if k != "meeting_topics"}
        result = parse_extraction_response(json.dumps(data))
        assert result["topics"] == []

    def test_missing_type_defaults_other(self):
        data = {k: v for k, v in VALID_EXTENDED.items() if k != "meeting_type"}
        result = parse_extraction_response(json.dumps(data))
        assert result["meeting_type"] == "other"

    def test_invalid_type_defaults_other(self):
        data = {**VALID_EXTENDED, "meeting_type": "not_a_real_type"}
        result = parse_extraction_response(json.dumps(data))
        assert result["meeting_type"] == "other"

    def test_missing_summary_defaults_empty_string(self):
        data = {k: v for k, v in VALID_EXTENDED.items() if k != "meeting_summary"}
        result = parse_extraction_response(json.dumps(data))
        assert result["summary"] == ""

    def test_missing_tags_on_commitment_defaults_empty_list(self):
        commitment_without_tags = {k: v for k, v in VALID_EXTENDED["commitments"][0].items() if k != "tags"}
        data = {**VALID_EXTENDED, "commitments": [commitment_without_tags]}
        result = parse_extraction_response(json.dumps(data))
        assert result["commitments"][0]["tags"] == []

    def test_tags_normalised_to_lowercase(self):
        commitment = {**VALID_EXTENDED["commitments"][0], "tags": ["Q2 Board Prep", "PRICING"]}
        data = {**VALID_EXTENDED, "commitments": [commitment]}
        result = parse_extraction_response(json.dumps(data))
        assert result["commitments"][0]["tags"] == ["q2 board prep", "pricing"]

    # --- Backward compat: flat array treated as commitments ---

    def test_flat_array_backward_compat(self):
        flat = json.dumps([VALID_EXTENDED["commitments"][0]])
        result = parse_extraction_response(flat)
        assert len(result["commitments"]) == 1
        assert result["topics"] == []
        assert result["meeting_type"] == "other"
        assert result["summary"] == ""

    # --- Garbage / failure inputs ---

    def test_empty_string_returns_safe_defaults(self):
        result = parse_extraction_response("")
        assert result["commitments"] == []
        assert result["topics"] == []
        assert result["meeting_type"] == "other"
        assert result["summary"] == ""

    def test_garbage_input_returns_safe_defaults(self):
        result = parse_extraction_response("I cannot help with that.")
        assert result["commitments"] == []

    def test_partial_json_returns_safe_defaults(self):
        result = parse_extraction_response('{"commitments": [{"raw_text": "incomplete')
        assert result["commitments"] == []

    def test_all_meeting_type_choices_accepted(self):
        valid_types = ["leadership", "one_on_one", "team", "project", "board", "external", "other"]
        for mt in valid_types:
            data = {**VALID_EXTENDED, "meeting_type": mt}
            result = parse_extraction_response(json.dumps(data))
            assert result["meeting_type"] == mt, f"Expected {mt} to be accepted"
