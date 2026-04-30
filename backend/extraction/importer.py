import logging

from google import genai
from django.conf import settings

from .prompt_builder import build_import_prompt
from .parser import safe_json_parse

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )


def extract_from_document(text: str) -> list[dict]:
    """
    Extract commitments from a prior-commitments document via Gemini.

    The document may be a Notion export, spreadsheet paste, email thread,
    or any plain-text action-item list.  Unlike transcript extraction, there
    is no participant list — owner names are taken directly from the document.

    Each returned item has source='import' so the caller can tag Commitment
    records with the correct source value.

    Returns [] on empty input or Gemini failure.
    """
    if not text or not text.strip():
        return []

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
        return []

    commitments = safe_json_parse(raw)
    for item in commitments:
        item["source"] = "import"

    logger.info("extract_from_document: extracted=%d items", len(commitments))
    return commitments
