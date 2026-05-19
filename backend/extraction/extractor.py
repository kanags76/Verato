import logging

from google import genai
from django.conf import settings

from .prompt_builder import build_transcript_prompt
from .parser import parse_extraction_response

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if api_key:
        return genai.Client(api_key=api_key)
    # Local dev fallback: Vertex AI via ADC (gcloud auth application-default login)
    return genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )


def extract_commitments(
    transcript: str,
    participants: list[str],
    meeting_title: str = "",
    meeting_date: str = "",
) -> dict:
    """
    Extract commitments, topics, meeting type, and summary from a transcript via Gemini.

    Returns a dict:
      {
        "commitments":  list[dict],   commitment objects with tags[]
        "topics":       list[dict],   [{"label": str, "confidence": float}]
        "meeting_type": str,          e.g. "leadership", "one_on_one", "team"
        "summary":      str,          2-3 sentence meeting digest
      }

    Returns empty defaults on empty input or Gemini failure — never raises.
    """
    _empty = {"commitments": [], "topics": [], "meeting_type": "other", "summary": ""}

    if not transcript or not transcript.strip():
        return _empty

    prompt = build_transcript_prompt(transcript, participants, meeting_title, meeting_date)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_EXTRACTION_MODEL,
            contents=prompt,
        )
        raw = response.text
    except Exception as exc:
        logger.error("extract_commitments: Gemini call failed: %s", exc)
        return _empty

    result = parse_extraction_response(raw)
    logger.info(
        "extract_commitments: title=%r participants=%d commitments=%d topics=%d type=%s",
        meeting_title, len(participants),
        len(result["commitments"]), len(result["topics"]), result["meeting_type"],
    )
    return result
