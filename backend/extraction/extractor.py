import logging

from google import genai
from django.conf import settings

from .prompt_builder import build_transcript_prompt
from .parser import safe_json_parse

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
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
) -> list[dict]:
    """
    Extract explicit commitments from a meeting transcript via Gemini.

    Args:
        transcript:    Full transcript text.
        participants:  Names of meeting participants (used for pronoun resolution).
        meeting_title: Optional title for prompt context.
        meeting_date:  Optional ISO date (YYYY-MM-DD) for deadline resolution.

    Returns:
        List of commitment dicts matching the extraction output schema.
        Returns [] on empty input or Gemini failure.
    """
    if not transcript or not transcript.strip():
        return []

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
        return []

    commitments = safe_json_parse(raw)
    logger.info(
        "extract_commitments: title=%r participants=%d extracted=%d",
        meeting_title, len(participants), len(commitments),
    )
    return commitments
