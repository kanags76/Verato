import logging

from django.conf import settings
from google import genai

from .prompt_builder import build_import_prompt
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


def extract_from_document(text: str) -> dict:
    """
    Extract commitments from a prior-commitments document via Gemini.
    Returns empty defaults on empty input or Gemini failure — never raises.
    """
    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not text or not text.strip():
        return _empty

    prompt = build_import_prompt(text)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_EXTRACTION_MODEL,
            contents=prompt,
        )
        raw = response.text
    except Exception as exc:
        logger.error("extract_from_document: Gemini call failed: %s", exc)
        return _empty

    result = parse_extraction_response(raw)
    for item in result["commitments"]:
        item["source"] = "import"

    logger.info("extract_from_document: extracted=%d items", len(result["commitments"]))
    return result
