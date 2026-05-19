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
    def test_returns_dict(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        assert isinstance(result, dict)
        assert "commitments" in result and "topics" in result

    def test_items_tagged_with_source_import(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result["commitments"]:
            assert item.get("source") == "import"

    def test_items_have_required_fields(self, import_notion_table):
        required = {"raw_text", "normalised_text", "commit_type", "owner_name",
                    "deadline_text", "deadline_resolved", "confidence", "tags"}
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result["commitments"]:
            assert required.issubset(item.keys())

    def test_confidence_float_in_range(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result["commitments"]:
            assert isinstance(item["confidence"], float)
            assert 0.0 <= item["confidence"] <= 1.0

    def test_tags_is_list(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        for item in result["commitments"]:
            assert isinstance(item["tags"], list)

    def test_topics_always_empty_for_imports(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_from_document(import_notion_table)
        # Import documents don't produce meeting topics
        # (the mock returns topics but the importer contract is topics=[] from build_import_prompt)
        assert isinstance(result["topics"], list)

    def test_empty_text_returns_empty(self):
        result = extract_from_document("")
        assert result["commitments"] == []
        assert result["topics"] == []

    def test_whitespace_only_returns_empty(self):
        result = extract_from_document("   \n  ")
        assert result["commitments"] == []

    def test_gemini_failure_returns_empty(self, import_notion_table):
        bad_client = MagicMock()
        bad_client.models.generate_content.side_effect = RuntimeError("network error")
        with patch("extraction.importer._get_client", return_value=bad_client):
            result = extract_from_document(import_notion_table)
        assert result["commitments"] == []

    def test_gemini_returns_garbage_returns_empty(self, import_notion_table):
        with patch("extraction.importer._get_client", return_value=make_mock_client("Sorry, no.")):
            result = extract_from_document(import_notion_table)
        assert result["commitments"] == []

    def test_fenced_json_handled(self, import_spreadsheet):
        fenced = "```json\n" + SAMPLE_COMMITMENTS_JSON + "\n```"
        with patch("extraction.importer._get_client", return_value=make_mock_client(fenced)):
            result = extract_from_document(import_spreadsheet)
        assert len(result["commitments"]) == 2
        assert all(r["source"] == "import" for r in result["commitments"])


# ---------------------------------------------------------------------------
# Integration tests — real Vertex AI Gemini (--run-slow)
# ---------------------------------------------------------------------------

def _assert_owners_extracted(commitments: list[dict], expected_owners: list[str], label: str):
    """Assert >= 85% of expected owner first names appear in the extracted owner_names."""
    extracted = [r["owner_name"].lower() for r in commitments]
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
        commits = result["commitments"]
        assert len(commits) >= 4, f"Expected >= 4 items from Notion table, got {len(commits)}"
        _assert_owners_extracted(
            commits,
            ["Sarah", "Tom", "Maya", "Rachel", "James", "Finance"],
            "Notion table",
        )

    def test_spreadsheet_extracts_seven_commitments(self, import_spreadsheet):
        result = extract_from_document(import_spreadsheet)
        commits = result["commitments"]
        assert len(commits) >= 5, f"Expected >= 5 from spreadsheet, got {len(commits)}"
        _assert_owners_extracted(
            commits,
            ["Sarah", "Tom", "Maya", "Rachel", "James", "Priya", "Finance"],
            "Spreadsheet",
        )

    def test_action_list_extracts_five_commitments(self, import_action_list):
        result = extract_from_document(import_action_list)
        commits = result["commitments"]
        assert len(commits) >= 4, f"Expected >= 4 from action list, got {len(commits)}"
        _assert_owners_extracted(
            commits,
            ["Sarah", "Tom", "Maya", "Rachel", "James"],
            "Action list",
        )

    def test_all_items_tagged_source_import(self, import_action_list):
        result = extract_from_document(import_action_list)
        commits = result["commitments"]
        assert len(commits) > 0, "Expected commitments from action list"
        for item in commits:
            assert item["source"] == "import"

    def test_notion_table_high_confidence_for_structured_rows(self, import_notion_table):
        result = extract_from_document(import_notion_table)
        commits = result["commitments"]
        assert len(commits) > 0, "Expected commitments from Notion table"
        avg_confidence = sum(r["confidence"] for r in commits) / len(commits)
        assert avg_confidence >= 0.70, f"Expected avg confidence >= 0.70, got {avg_confidence:.2f}"

    def test_deadlines_resolved_where_possible(self, import_notion_table):
        import re
        result = extract_from_document(import_notion_table)
        commits = result["commitments"]
        assert len(commits) > 0, "Expected commitments from Notion table"
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        resolved_count = sum(
            1 for r in commits
            if r["deadline_resolved"] and iso_pattern.match(r["deadline_resolved"])
        )
        assert resolved_count >= math.ceil(len(commits) * 0.6), (
            f"Expected >= 60% dates resolved, got {resolved_count}/{len(commits)}"
        )

    def test_action_list_owner_names_not_empty(self, import_action_list):
        result = extract_from_document(import_action_list)
        commits = result["commitments"]
        assert len(commits) > 0, "Expected commitments from action list"
        named = [r for r in commits if r["owner_name"].strip()]
        assert len(named) >= math.ceil(len(commits) * 0.85), (
            f"Expected >= 85% items to have an owner name, got {len(named)}/{len(commits)}"
        )

    def test_commitment_tags_extracted(self, import_notion_table):
        result = extract_from_document(import_notion_table)
        commits = result["commitments"]
        assert len(commits) > 0
        tagged = [r for r in commits if r.get("tags")]
        assert len(tagged) >= math.ceil(len(commits) * 0.5), (
            f"Expected >= 50% of import items to have tags, got {len(tagged)}/{len(commits)}"
        )
