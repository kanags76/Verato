import logging

from google import genai
from django.conf import settings

from .prompt_builder import build_transcript_prompt, build_pass2_prompt
from .parser import parse_extraction_response

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )


def _call_gemini(prompt: str) -> str | None:
    """Send a prompt to Gemini and return the raw text response. Returns None on failure."""
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_EXTRACTION_MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        return None


def extract_commitments(
    transcript: str,
    participants: list[str],
    meeting_title: str = "",
    meeting_date: str = "",
) -> dict:
    """
    Pass 1 extraction. Returns commitments, topics, meeting_type, summary,
    participants, and clarifications.

    If clarifications is non-empty the caller should pause and collect answers
    before calling extract_commitments_pass2.

    Never raises — returns empty defaults on failure.
    """
    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not transcript or not transcript.strip():
        return _empty

    prompt = build_transcript_prompt(transcript, participants, meeting_title, meeting_date)
    raw = _call_gemini(prompt)
    if raw is None:
        return _empty

    result = parse_extraction_response(raw)
    logger.info(
        "extract_commitments (pass1): title=%r participants=%d "
        "commitments=%d topics=%d clarifications=%d type=%s",
        meeting_title, len(participants),
        len(result["commitments"]), len(result["topics"]),
        len(result["clarifications"]), result["meeting_type"],
    )
    return result


def extract_commitments_pass2(
    transcript: str,
    participants: list[str],
    clarifications: list[dict],
    meeting_title: str = "",
    meeting_date: str = "",
) -> dict:
    """
    Pass 2 extraction. Called after the CoS has answered all clarification questions.
    clarifications: list of {"question": str, "answer": str}

    Returns same shape as extract_commitments but clarifications will be [].
    Never raises.
    """
    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not transcript or not transcript.strip():
        return _empty

    prompt = build_pass2_prompt(transcript, participants, meeting_title, meeting_date, clarifications)
    raw = _call_gemini(prompt)
    if raw is None:
        return _empty

    result = parse_extraction_response(raw)
    logger.info(
        "extract_commitments (pass2): title=%r participants=%d "
        "commitments=%d topics=%d type=%s",
        meeting_title, len(participants),
        len(result["commitments"]), len(result["topics"]), result["meeting_type"],
    )
    return result


