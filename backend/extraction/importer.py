import logging

from .prompt_builder import build_import_prompt
from .parser import parse_extraction_response

logger = logging.getLogger(__name__)


def extract_from_document(text: str, log_context: dict | None = None) -> dict:
    """
    Extract commitments from a prior-commitments document via Gemini.
    Returns empty defaults on empty input or Gemini failure — never raises.
    log_context: optional dict with keys organisation, meeting_id passed to AICallLog.
    """
    from apps.prompts.logger import call_gemini

    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not text or not text.strip():
        return _empty

    prompt = build_import_prompt(text)
    raw = call_gemini(prompt, 'import_extraction', **(log_context or {}))
    if raw is None:
        return _empty

    result = parse_extraction_response(raw)
    for item in result["commitments"]:
        item["source"] = "import"

    logger.info("extract_from_document: extracted=%d items", len(result["commitments"]))
    return result
