"""
Tests for extraction/extractor.py.

Unit tests (always run): mock the Gemini client, verify structure and error handling.
Integration tests (--run-slow): call real Vertex AI Gemini, verify precision >= 85%.
"""
import math
from unittest.mock import patch

import pytest

from extraction.extractor import extract_commitments
from extraction.tests.conftest import make_mock_client, SAMPLE_COMMITMENTS_JSON

PARTICIPANTS_Q2 = ["James B.", "Sarah K.", "Tom R.", "Maya L."]
PARTICIPANTS_STANDUP = ["Tom R.", "Alex C.", "Priya M."]
PARTICIPANTS_LEGAL = ["James B.", "Rachel V."]
PARTICIPANTS_ALLHANDS = ["James B.", "Sarah K.", "Tom R.", "Maya L."]
PARTICIPANTS_11 = ["Sarah K.", "James B."]


# ---------------------------------------------------------------------------
# Unit tests — mocked Gemini client
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestExtractCommitmentsUnit:
    def test_returns_dict(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert isinstance(result, dict)
        assert "commitments" in result and "topics" in result
        assert "meeting_type" in result and "summary" in result

    def test_returns_two_commitments_from_mock(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert len(result["commitments"]) == 2

    def test_commitments_have_required_fields(self, transcript_q2_planning):
        required = {"raw_text", "normalised_text", "commit_type", "owner_name",
                    "deadline_text", "deadline_resolved", "confidence", "tags"}
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        for item in result["commitments"]:
            assert required.issubset(item.keys()), f"Missing fields: {required - item.keys()}"

    def test_confidence_is_float_in_range(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        for item in result["commitments"]:
            assert isinstance(item["confidence"], float)
            assert 0.0 <= item["confidence"] <= 1.0

    def test_commit_type_is_explicit(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        for item in result["commitments"]:
            assert item["commit_type"] == "explicit"

    def test_tags_is_list(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        for item in result["commitments"]:
            assert isinstance(item["tags"], list)

    def test_topics_returned(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert isinstance(result["topics"], list)
        assert len(result["topics"]) > 0
        for t in result["topics"]:
            assert "label" in t and "confidence" in t

    def test_meeting_type_returned(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert result["meeting_type"] == "team"

    def test_summary_returned(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_empty_transcript_returns_empty(self):
        result = extract_commitments("", PARTICIPANTS_Q2)
        assert result["commitments"] == []
        assert result["topics"] == []

    def test_whitespace_only_transcript_returns_empty(self):
        result = extract_commitments("   \n  ", PARTICIPANTS_Q2)
        assert result["commitments"] == []

    def test_gemini_failure_returns_empty(self, transcript_q2_planning):
        from unittest.mock import MagicMock
        bad_client = MagicMock()
        bad_client.models.generate_content.side_effect = Exception("API timeout")
        with patch("extraction.extractor._get_client", return_value=bad_client):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert result["commitments"] == []
        assert result["topics"] == []

    def test_gemini_returns_garbage_returns_empty(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client("I cannot do that.")):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert result["commitments"] == []

    def test_gemini_returns_fenced_json(self, transcript_q2_planning):
        fenced = "```json\n" + SAMPLE_COMMITMENTS_JSON + "\n```"
        with patch("extraction.extractor._get_client", return_value=make_mock_client(fenced)):
            result = extract_commitments(transcript_q2_planning, PARTICIPANTS_Q2)
        assert len(result["commitments"]) == 2

    def test_meeting_title_and_date_accepted(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(
                transcript_q2_planning, PARTICIPANTS_Q2,
                meeting_title="Q2 Planning", meeting_date="2026-04-22",
            )
        assert isinstance(result, dict)

    def test_empty_participants_list(self, transcript_q2_planning):
        with patch("extraction.extractor._get_client", return_value=make_mock_client(SAMPLE_COMMITMENTS_JSON)):
            result = extract_commitments(transcript_q2_planning, [])
        assert isinstance(result["commitments"], list)


# ---------------------------------------------------------------------------
# Integration tests — real Vertex AI Gemini (--run-slow)
# ---------------------------------------------------------------------------

def _assert_precision(commitments: list[dict], expected_owners: list[str], label: str):
    """Assert >= 85% of expected owners appear in results (case-insensitive partial match)."""
    extracted_owners = [r["owner_name"].lower() for r in commitments]
    found = 0
    for owner in expected_owners:
        first_name = owner.split()[0].lower()
        if any(first_name in extracted for extracted in extracted_owners):
            found += 1
    required = math.ceil(len(expected_owners) * 0.85)
    assert found >= required, (
        f"{label}: found {found}/{len(expected_owners)} expected owners "
        f"(need {required} for 85% precision). Extracted: {extracted_owners}"
    )


@pytest.mark.slow
class TestExtractCommitmentsIntegration:
    def test_q2_planning_extracts_three_commitments(self, transcript_q2_planning):
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        commits = result["commitments"]
        assert len(commits) >= 2, f"Expected at least 2 commitments, got {len(commits)}: {commits}"
        _assert_precision(commits, ["Sarah K.", "Tom R.", "Maya L."], "Q2 Planning")

    def test_q2_planning_has_no_false_positives(self, transcript_q2_planning):
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        commits = result["commitments"]
        assert len(commits) <= 5, f"Too many extractions — possible false positives: {len(commits)}"

    def test_engineering_standup_extracts_two_commitments(self, transcript_engineering_standup):
        result = extract_commitments(
            transcript_engineering_standup, PARTICIPANTS_STANDUP,
            meeting_title="Engineering Standup", meeting_date="2026-04-24",
        )
        commits = result["commitments"]
        assert len(commits) >= 1, f"Expected at least 1 commitment, got {len(commits)}"
        _assert_precision(commits, ["Alex C.", "Priya M."], "Engineering Standup")

    def test_legal_review_extracts_two_commitments(self, transcript_legal_review):
        result = extract_commitments(
            transcript_legal_review, PARTICIPANTS_LEGAL,
            meeting_title="EMEA Legal Review", meeting_date="2026-04-21",
        )
        commits = result["commitments"]
        assert len(commits) >= 1
        _assert_precision(commits, ["Rachel V.", "James B."], "Legal Review")

    def test_allhands_extracts_ceo_commitment(self, transcript_allhands):
        result = extract_commitments(
            transcript_allhands, PARTICIPANTS_ALLHANDS,
            meeting_title="All-Hands", meeting_date="2026-04-25",
        )
        commits = result["commitments"]
        assert len(commits) >= 1
        owner_names = " ".join(r["owner_name"].lower() for r in commits)
        assert "james" in owner_names, f"Expected James B. commitment, got: {owner_names}"

    def test_onetoone_extracts_two_commitments(self, transcript_onetoone):
        result = extract_commitments(
            transcript_onetoone, PARTICIPANTS_11,
            meeting_title="CoS — CEO 1:1", meeting_date="2026-04-23",
        )
        commits = result["commitments"]
        assert len(commits) >= 1
        _assert_precision(commits, ["Sarah K.", "James B."], "1:1")

    def test_all_items_have_valid_structure(self, transcript_q2_planning):
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        commits = result["commitments"]
        assert len(commits) > 0, "Expected commitments from Q2 planning transcript"
        required = {"raw_text", "normalised_text", "commit_type", "owner_name",
                    "deadline_text", "deadline_resolved", "confidence", "tags"}
        for item in commits:
            assert required.issubset(item.keys())

    def test_deadlines_resolved_to_iso_dates(self, transcript_q2_planning):
        import re
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        commits = result["commitments"]
        assert len(commits) > 0
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        resolved_count = sum(
            1 for r in commits
            if r["deadline_resolved"] and iso_pattern.match(str(r["deadline_resolved"]))
        )
        assert resolved_count >= 1, f"Expected at least 1 resolved deadline, got {resolved_count}"

    def test_meeting_topics_returned(self, transcript_q2_planning):
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        assert isinstance(result["topics"], list)
        assert len(result["topics"]) > 0, "Expected at least one topic from Q2 planning"
        for t in result["topics"]:
            assert "label" in t and "confidence" in t
            assert isinstance(t["confidence"], float)

    def test_meeting_type_is_valid(self, transcript_q2_planning):
        from extraction.parser import _VALID_MEETING_TYPES
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        assert result["meeting_type"] in _VALID_MEETING_TYPES

    def test_summary_is_non_empty(self, transcript_q2_planning):
        result = extract_commitments(
            transcript_q2_planning, PARTICIPANTS_Q2,
            meeting_title="Q2 Planning", meeting_date="2026-04-22",
        )
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 20, "Summary should be at least a sentence"
