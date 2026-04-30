import json
import re
import logging

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {
    "raw_text", "normalised_text", "commit_type",
    "owner_name", "deadline_text", "deadline_resolved", "confidence",
}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


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
