def build_transcript_prompt(
    transcript: str,
    participants: list[str],
    meeting_title: str = "",
    meeting_date: str = "",
) -> str:
    """
    Build the Gemini prompt for extracting commitments from a meeting transcript.
    Returns the Week 3.5 extended JSON format (commitments + topics + type + summary).
    """
    participants_str = ", ".join(participants) if participants else "unknown"

    context_lines = []
    if meeting_title:
        context_lines.append(f"Meeting title: {meeting_title}")
    if meeting_date:
        context_lines.append(
            f"Meeting date: {meeting_date}"
            " (use this to resolve relative deadlines such as 'end of Thursday',"
            " 'next week', 'by Friday')"
        )
    context_lines.append(f"Participants: {participants_str}")
    context = "\n".join(context_lines)

    return f"""You are an expert at extracting explicit commitments and thematic topics from meeting transcripts.

A commitment is when a specific person explicitly promises to deliver a specific thing by a specific time.

INCLUDE — clear explicit commitments:
  "I'll send you the report by Friday."
  "Tom will have the hiring brief to HR by May 2nd."
  "We'll complete the legal review before end of month."

EXCLUDE — everything that is not an explicit commitment:
  General discussion, brainstorming, or ideas
  Questions, requests, or suggestions ("we should...", "someone ought to...")
  Conditional statements ("if we get sign-off, we'll...")
  Status updates about already-completed actions
  Vague intentions with no clear owner or deliverable

{context}

Return a single JSON object with exactly these top-level keys:

"commitments" — array of commitment objects. For each commitment:
  "raw_text"         — verbatim sentence(s) from the transcript containing the commitment
  "normalised_text"  — clean third-person sentence with pronouns resolved to names from the participant list
  "commit_type"      — always the string "explicit"
  "owner_name"       — full name of the person making the commitment (match to participant list where possible)
  "deadline_text"    — exactly how the deadline was stated ("end of Thursday", "by May 2nd")
  "deadline_resolved"— ISO date YYYY-MM-DD resolved from meeting_date context, or null if cannot determine
  "confidence"       — float 0.0–1.0: your confidence this is a genuine, explicit commitment
  "tags"             — array of 1–3 lowercase 2-4 word noun-phrase strings labelling the theme of this commitment
                       e.g. ["q2 board prep", "pricing"] — must be a subset of meeting_topics labels

"meeting_topics" — array of thematic topic objects for the whole meeting (2–5 topics):
  "label"      — 2-4 word lowercase noun phrase e.g. "q2 board prep", "emea pricing", "senior hiring"
  "confidence" — float 0.0–1.0: confidence this is a genuine theme for the meeting

"meeting_type" — one of: leadership, one_on_one, team, project, board, external, other

"meeting_summary" — 2-3 sentence plain English summary of the meeting's key discussion and decisions

"participants" — array of strings: the full name of every person who spoke in the transcript,
  in order of first appearance. Include everyone, even if they made no commitments.
  Match to the provided participant list where possible; otherwise use the name as it appears.

Return ONLY valid JSON. No markdown fences. No explanation. No trailing text.
If no commitments are found, return an empty "commitments" array but still populate topics, type, and summary.

Transcript:
{transcript}"""


def build_import_prompt(text: str) -> str:
    """
    Build the Gemini prompt for extracting commitments from a prior-commitments document.
    Returns the Week 3.5 format — commitments with tags; topics and summary are empty for imports.
    """
    return f"""You are an expert at extracting action items and commitments from documents.

The document below may be a Notion table export, a spreadsheet paste, an email thread, meeting notes,
or a plain text list of action items. Extract every item that represents a clear, actionable commitment:
a specific person owes a specific deliverable, ideally by a specific date.

Return a single JSON object with exactly these top-level keys:

"commitments" — array of commitment objects. For each item:
  "raw_text"         — the original text exactly as it appears in the document
  "normalised_text"  — a clean, complete sentence describing the commitment
  "commit_type"      — always the string "explicit"
  "owner_name"       — person responsible (empty string "" if genuinely unclear)
  "deadline_text"    — how the deadline appears in the document (empty string if absent)
  "deadline_resolved"— ISO date YYYY-MM-DD if determinable, otherwise null
  "confidence"       — float 0.0–1.0:
                       0.9+ for structured rows with clear owner + date
                       0.7–0.89 for items missing owner or date but clearly a commitment
                       below 0.7 for vague or ambiguous items
  "tags"             — array of 1–3 lowercase 2-4 word noun-phrase strings labelling the theme
                       e.g. ["q2 board prep", "vendor selection"]

"meeting_topics"  — empty array []
"meeting_type"    — the string "other"
"meeting_summary" — empty string ""

Return ONLY valid JSON. No markdown fences. No explanation.
If no commitments are found, return an empty "commitments" array.

Document:
{text}"""
