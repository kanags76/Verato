"""Utility to detect speaker names from a raw transcript."""
import re


# Patterns that look like speaker labels but aren't real names
_SKIP_LABELS = {
    'SPEAKER', 'MODERATOR', 'HOST', 'ALL', 'EVERYONE',
    'INTERVIEWER', 'INTERVIEWEE', 'FACILITATOR', 'PARTICIPANT',
    'UNKNOWN', 'INAUDIBLE',
}
_SPEAKER_NUM_RE = re.compile(r'^speaker[\s_\-]?\d+$', re.IGNORECASE)


def scan_speakers(transcript: str) -> list[str]:
    """
    Return unique speaker names detected in the transcript, in order of first appearance.

    Handles formats:
      Alice Chen: text
      [Bob Smith]: text
      (Carol): text
      SPEAKER 1: text   ← skipped
    """
    pattern = re.compile(
        r'^[\[\(]?([A-Z][a-zA-Z\s\.\-\']{1,50}?)[\]\)]?\s*:',
        re.MULTILINE,
    )
    seen: set[str] = set()
    names: list[str] = []

    for match in pattern.finditer(transcript):
        name = match.group(1).strip()
        upper = name.upper()
        if upper in _SKIP_LABELS:
            continue
        if _SPEAKER_NUM_RE.match(name):
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)

    return names


def suggest_person_match(org, speaker_name: str):
    """
    Return the best-matching Person in the org for a detected speaker name, or None.
    Tries exact match first, then first-name/last-name partial match.
    """
    from apps.accounts.models import Person

    # Exact case-insensitive
    exact = Person.objects.filter(organisation=org, name__iexact=speaker_name).first()
    if exact:
        return exact

    # Word-level partial match (any word > 3 chars)
    words = [w for w in speaker_name.split() if len(w) > 3]
    for word in words:
        match = Person.objects.filter(
            organisation=org,
            name__icontains=word,
        ).first()
        if match:
            return match

    return None
