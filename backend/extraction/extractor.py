import logging

from .prompt_builder import build_transcript_prompt, build_pass2_prompt
from .parser import parse_extraction_response

logger = logging.getLogger(__name__)


def extract_commitments(
    transcript: str,
    participants: list[str],
    meeting_title: str = "",
    meeting_date: str = "",
    log_context: dict | None = None,
) -> dict:
    """
    Pass 1 extraction. Returns commitments, topics, meeting_type, summary,
    participants, and clarifications.

    If clarifications is non-empty the caller should pause and collect answers
    before calling extract_commitments_pass2.

    Never raises — returns empty defaults on failure.
    log_context: optional dict with keys organisation, meeting_id passed to AICallLog.
    """
    from apps.prompts.logger import call_gemini

    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not transcript or not transcript.strip():
        return _empty

    prompt = build_transcript_prompt(transcript, participants, meeting_title, meeting_date)
    raw = call_gemini(prompt, 'transcript_extraction', **(log_context or {}))
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
    log_context: dict | None = None,
) -> dict:
    """
    Pass 2 extraction. Called after the CoS has answered all clarification questions.
    clarifications: list of {"question": str, "answer": str}

    Returns same shape as extract_commitments but clarifications will be [].
    Never raises.
    """
    from apps.prompts.logger import call_gemini

    _empty = {"commitments": [], "topics": [], "meeting_type": "other",
              "summary": "", "participants": [], "clarifications": []}

    if not transcript or not transcript.strip():
        return _empty

    prompt = build_pass2_prompt(transcript, participants, meeting_title, meeting_date, clarifications)
    raw = call_gemini(prompt, 'transcript_pass2', **(log_context or {}))
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


# Keep _call_gemini available for any legacy callers — delegates to logger
def _call_gemini(prompt: str) -> str | None:
    from apps.prompts.logger import call_gemini
    return call_gemini(prompt, 'unknown')
