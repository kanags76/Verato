"""
Tests for extraction/importer.py.

Unit tests (always run): mock the Gemini client, verify structure and error handling.
Integration tests (--run-slow): call real Vertex AI Gemini, verify owner + deadline extraction.
"""
import math
from unittest.mock import MagicMock, patch

import pytest

from extraction.importer import extract_from_document
from extraction.tests.conftest import make_mock_client, SAMPLE_COMMITMENTS_JSON


# ---------------------------------------------------------------------------
# Unit tests — mocked Gemini client
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestExtractFromDocumentUnit:
    def test_returns_list(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        assert isinstance(result, list)

    def test_items_tagged_with_source_import(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result:
            assert item.get("source") == "import"

    def test_items_have_required_fields(self, import_notion_table):
        required = {"raw_text", "normalised_text", "commit_type", "owner_name",
                    "deadline_text", "deadline_resolved", "confidence"}
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result:
            assert required.issubset(item.keys())

    def test_confidence_float_in_range(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result:
            assert isinstance(item["confidence"], float)
            assert 0.0 <= item["confidence"] <= 1.0

    def test_empty_text_returns_empty(self):
        result = extract_from_document("")
        assert result == []

    def test_whitespace_only_returns_empty(self):
        result = extract_from_document("   \n  ")
        assert result == []

    def test_gemini_failure_returns_empty(self, import_notion_table):
        bad_client = MagicMock()
        bad_client.models.generate_content.side_effect = RuntimeError("network error")
        with patch("extraction.importer._get_client", return_value=bad_client):
            result = extract_from_document(import_notion_table)
        assert result == []

    def test_gemini_returns_garbage_returns_empty(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client("Sorry, no.")):
            result = extract_from_document(import_notion_table)
        assert result == []

    def test_fenced_json_handled(self, import_spreadsheet):
        fenced = "```json\n" + SAMPLE_COMMITMENTS_JSON + "\n```"
        with patch("extraction.importer._get_client", return_value=make_mock_client(fenced)):
            result = extract_from_document(import_spreadsheet)
        assert len(result) == 2
        assert all(r["source"] == "import" for r in result)


# ---------------------------------------------------------------------------
# Integration tests — real Vertex AI Gemini (--run-slow)
# ---------------------------------------------------------------------------

def _assert_owners_extracted(results: list[dict], expected_owners: list[str], label: str):
    """Assert >= 85% of expected owner first names appear in the extracted owner_names."""
    extracted = [r["owner_name"].lower() for r in results]
    found = 0
    for owner in expected_owners:
        first_name = owner.split()[0].lower()
        if any(first_name in e for e in extracted):
            found += 1
    required = math.ceil(len(expected_owners) * 0.85)
    assert found >= required, (
        f"{label}: found {found}/{len(expected_owners)} owners "
        f"(need {required}). Extracted: {extracted}"
    )


@pytest.mark.slow
class TestExtractFromDocumentIntegration:
    def test_notion_table_extracts_six_commitments(self, import_notion_table):
        result = extract_from_document(import_notion_table)
        assert len(result) >= 4, f"Expected >= 4 items from Notion table, got {len(result)}"
        _assert_owners_extracted(
            result,
            ["Sarah", "Tom", "Maya", "Rachel", "James", "Finance"],
            "Notion table",
        )

    def test_spreadsheet_extracts_seven_commitments(self, import_spreadsheet):
        result = extract_from_document(import_spreadsheet)
        assert len(result) >= 5, f"Expected >= 5 from spreadsheet, got {len(result)}"
        _assert_owners_extracted(
            result,
            ["Sarah", "Tom", "Maya", "Rachel", "James", "Priya", "Finance"],
            "Spreadsheet",
        )

    def test_action_list_extracts_five_commitments(self, import_action_list):
        result = extract_from_document(import_action_list)
        assert len(result) >= 4, f"Expected >= 4 from action list, got {len(result)}"
        _assert_owners_extracted(
            result,
            ["Sarah", "Tom", "Maya", "Rachel", "James"],
            "Action list",
        )

    def test_all_items_tagged_source_import(self, import_action_list):
        result = extract_from_document(import_action_list)
        assert len(result) > 0, "Expected commitments from action list"
        for item in result:
            assert item["source"] == "import"

    def test_notion_table_high_confidence_for_structured_rows(self, import_notion_table):
        result = extract_from_document(import_notion_table)
        assert len(result) > 0, "Expected commitments from Notion table"
        avg_confidence = sum(r["confidence"] for r in result) / len(result)
        assert avg_confidence >= 0.70, f"Expected avg confidence >= 0.70, got {avg_confidence:.2f}"

    def test_deadlines_resolved_where_possible(self, import_notion_table):
        import re
        result = extract_from_document(import_notion_table)
        assert len(result) > 0, "Expected commitments from Notion table"
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        resolved_count = sum(
            1 for r in result
            if r["deadline_resolved"] and iso_pattern.match(r["deadline_resolved"])
        )
        assert resolved_count >= math.ceil(len(result) * 0.6), (
            f"Expected >= 60% dates resolved, got {resolved_count}/{len(result)}"
        )

    def test_action_list_owner_names_not_empty(self, import_action_list):
        result = extract_from_document(import_action_list)
        assert len(result) > 0, "Expected commitments from action list"
        named = [r for r in result if r["owner_name"].strip()]
        assert len(named) >= math.ceil(len(result) * 0.85), (
            f"Expected >= 85% items to have an owner name, got {len(named)}/{len(result)}"
        )
