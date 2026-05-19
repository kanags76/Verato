import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text()


@pytest.fixture
def transcript_q2_planning():
    return _load_fixture("transcript_01_q2_planning.txt")


@pytest.fixture
def transcript_engineering_standup():
    return _load_fixture("transcript_02_engineering_standup.txt")


@pytest.fixture
def transcript_legal_review():
    return _load_fixture("transcript_03_legal_review.txt")


@pytest.fixture
def transcript_allhands():
    return _load_fixture("transcript_04_allhands.txt")


@pytest.fixture
def transcript_onetoone():
    return _load_fixture("transcript_05_onetoone.txt")


@pytest.fixture
def import_notion_table():
    return _load_fixture("import_01_notion_table.txt")


@pytest.fixture
def import_spreadsheet():
    return _load_fixture("import_02_spreadsheet.txt")


@pytest.fixture
def import_action_list():
    return _load_fixture("import_03_action_list.txt")


def make_mock_client(response_text: str) -> MagicMock:
    """Return a mock genai Client whose generate_content returns response_text."""
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_response

    mock_client = MagicMock()
    mock_client.models = mock_models
    return mock_client


# Week 3.5 format — the dict structure returned by extract_commitments() and extract_from_document().
SAMPLE_EXTRACTION_RESPONSE = {
    "commitments": [
        {
            "raw_text": "I'll have the report to you by Friday.",
            "normalised_text": "Alice will deliver the report by Friday.",
            "commit_type": "explicit",
            "owner_name": "Alice",
            "deadline_text": "by Friday",
            "deadline_resolved": "2026-05-01",
            "confidence": 0.93,
            "tags": ["report delivery"],
        },
        {
            "raw_text": "I'll send the contract to legal by end of day.",
            "normalised_text": "Bob will send the contract to legal by end of day.",
            "commit_type": "explicit",
            "owner_name": "Bob",
            "deadline_text": "end of day",
            "deadline_resolved": None,
            "confidence": 0.87,
            "tags": ["legal review", "contract"],
        },
    ],
    "meeting_topics": [
        {"label": "report delivery", "confidence": 0.95},
        {"label": "legal review",    "confidence": 0.88},
        {"label": "contract",        "confidence": 0.82},
    ],
    "meeting_type": "team",
    "meeting_summary": "Team reviewed report delivery timeline and contract handover to legal.",
}

# JSON string of the above — passed to make_mock_client() in tests.
SAMPLE_COMMITMENTS_JSON = json.dumps(SAMPLE_EXTRACTION_RESPONSE)
