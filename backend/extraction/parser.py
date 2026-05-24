import json
import re
import logging

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {
    "raw_text", "normalised_text", "commit_type",
    "owner_name", "deadline_text", "deadline_resolved", "confidence",
}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

_VALID_MEETING_TYPES = {
    "leadership", "one_on_one", "team", "project", "board", "external", "other",
}
_TOPIC_CONFIDENCE_THRESHOLD = 0.60


def safe_json_parse(text: str) -> list[dict]:
    """
    Parse Gemini output into a validated list of commitment dicts.

    Handles:
    - Markdown code fences (```json ... ```)
    - Malformed or empty JSON — returns []
    - Non-array JSON — returns []
    - Items missing fields — fills defaults rather than dropping the item
    """
    if not text or not text.strip():
        return []

    cleaned = _FENCE_RE.sub("", text).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("safe_json_parse: decode failed (%s) | snippet: %.200s", exc, text)
        return []

    if not isinstance(data, list):
        logger.warning("safe_json_parse: expected list, got %s", type(data).__name__)
        return []

    results = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("safe_json_parse: item %d is not a dict — skipped", idx)
            continue

        # Apply field defaults so downstream code never needs to key-check
        item.setdefault("raw_text", "")
        item.setdefault("normalised_text", "")
        item.setdefault("commit_type", "explicit")
        item.setdefault("owner_name", "")
        item.setdefault("deadline_text", "")
        item.setdefault("deadline_resolved", None)
        item.setdefault("confidence", 0.5)

        try:
            item["confidence"] = float(item["confidence"])
            item["confidence"] = max(0.0, min(1.0, item["confidence"]))
        except (TypeError, ValueError):
            item["confidence"] = 0.5

        results.append(item)

    return results


def _apply_commitment_defaults(items: list) -> list[dict]:
    """Apply field defaults to raw commitment items, including the Week 3.5 tags field."""
    results = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            logger.warning("_apply_commitment_defaults: item %d is not a dict — skipped", idx)
            continue

        item.setdefault("raw_text", "")
        item.setdefault("normalised_text", "")
        item.setdefault("commit_type", "explicit")
        item.setdefault("owner_name", "")
        item.setdefault("deadline_text", "")
        item.setdefault("deadline_resolved", None)
        item.setdefault("confidence", 0.5)
        item.setdefault("tags", [])

        try:
            item["confidence"] = float(item["confidence"])
            item["confidence"] = max(0.0, min(1.0, item["confidence"]))
        except (TypeError, ValueError):
            item["confidence"] = 0.5

        if not isinstance(item["tags"], list):
            item["tags"] = []
        else:
            item["tags"] = [str(t).strip().lower() for t in item["tags"] if t]

        results.append(item)
    return results


def parse_extraction_response(text: str) -> dict:
    """
    Parse the Week 3.5 extended Gemini extraction response.

    Accepts both the new dict format and the old flat array (backward compat):
      New: {"commitments": [...], "meeting_topics": [...], "meeting_type": "...", "meeting_summary": "..."}
      Old: [{...}, {...}]  — treated as commitments with empty topics/type/summary

    Returns:
      {
        "commitments":  list[dict],   each item has a "tags" field (list of lowercase strings)
        "topics":       list[dict],   [{"label": str, "confidence": float}], only >= 0.60
        "meeting_type": str,          one of _VALID_MEETING_TYPES, defaults to "other"
        "summary":      str,          empty string if absent
      }

    Never raises — returns safe empty defaults on any parse failure.
    """
    _empty = {
        "commitments": [], "topics": [], "meeting_type": "other", "summary": "",
        "participants": [], "clarifications": [], "title": "",
    }

    if not text or not text.strip():
        return _empty

    cleaned = _FENCE_RE.sub("", text).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("parse_extraction_response: decode failed (%s) | snippet: %.200s", exc, text)
        return _empty

    # Backward compat: bare array → treat as commitments, empty graph metadata
    if isinstance(data, list):
        return {
            "commitments":    _apply_commitment_defaults(data),
            "topics":         [],
            "meeting_type":   "other",
            "summary":        "",
            "participants":   [],
            "clarifications": [],
            "title":          "",
        }

    if not isinstance(data, dict):
        logger.warning("parse_extraction_response: expected dict or list, got %s", type(data).__name__)
        return _empty

    # Extract commitments
    raw_commitments = data.get("commitments", [])
    if not isinstance(raw_commitments, list):
        raw_commitments = []

    # Extract and filter topics
    raw_topics = data.get("meeting_topics", [])
    if not isinstance(raw_topics, list):
        raw_topics = []
    topics = []
    for t in raw_topics:
        if not isinstance(t, dict):
            continue
        label = str(t.get("label", "")).strip().lower()
        if not label:
            continue
        try:
            confidence = float(t.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
        if confidence >= _TOPIC_CONFIDENCE_THRESHOLD:
            topics.append({"label": label, "confidence": confidence})

    # Validate meeting_type
    meeting_type = data.get("meeting_type", "other")
    if not isinstance(meeting_type, str) or meeting_type not in _VALID_MEETING_TYPES:
        meeting_type = "other"

    summary = data.get("meeting_summary", "") or ""

    raw_participants = data.get("participants", [])
    participants = []
    if isinstance(raw_participants, list):
        participants = [str(p).strip() for p in raw_participants if p and str(p).strip()]

    # Parse clarifications
    raw_clarifications = data.get("clarifications", [])
    clarifications = []
    if isinstance(raw_clarifications, list):
        for c in raw_clarifications:
            if not isinstance(c, dict):
                continue
            question = str(c.get("question", "")).strip()
            context  = str(c.get("context", "")).strip()
            if question:
                clarifications.append({"question": question, "context": context})

    suggested_title = str(data.get("meeting_title", "") or "").strip()

    return {
        "commitments":    _apply_commitment_defaults(raw_commitments),
        "topics":         topics,
        "meeting_type":   meeting_type,
        "summary":        str(summary),
        "participants":   participants,
        "clarifications": clarifications,
        "title":          suggested_title,
    }
