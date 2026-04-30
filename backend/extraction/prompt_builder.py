def build_transcript_prompt(
    transcript: str,
    participants: list[str],
    meeting_title: str = "",
    meeting_date: str = "",
) -> str:
    """
    Build the Gemini prompt for extracting commitments from a meeting transcript.

    meeting_date should be ISO format (YYYY-MM-DD) so the model can resolve
    relative deadlines like "end of Thursday" to a concrete date.
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

    return f"""You are an expert at extracting explicit commitments from meeting transcripts.

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

For each commitment found, return a JSON object with exactly these keys:
  "raw_text"         — verbatim sentence(s) from the transcript that contain the commitment
  "normalised_text"  — clean, third-person sentence with pronouns resolved to names from the participant list
  "commit_type"      — always the string "explicit"
  "owner_name"       — full name of the person making the commitment (match to participant list where possible)
  "deadline_text"    — exactly how the deadline was stated in the meeting (e.g. "end of Thursday", "by May 2nd")
  "deadline_resolved"— ISO date YYYY-MM-DD resolved from meeting_date context, or null if cannot determine
  "confidence"       — float 0.0–1.0: your confidence this is a genuine, explicit commitment

Return ONLY a valid JSON array. No markdown. No explanation. No trailing text.
If no commitments are found, return [].

Transcript:
{transcript}"""


def build_import_prompt(text: str) -> str:
    """
    Build the Gemini prompt for extracting commitments from a prior-commitments
    document (Notion export, spreadsheet, email thread, plain text action list).
    """
    return f"""You are an expert at extracting action items and commitments from documents.

The document below may be a Notion table export, a spreadsheet paste, an email thread, meeting notes,
or a plain text list of action items. Your job is to extract every item that represents a clear,
actionable commitment: a specific person owes a specific deliverable, ideally by a specific date.

For each item found, return a JSON object with exactly these keys:
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

Return ONLY a valid JSON array. No markdown. No explanation.
If no commitments are found, return [].

Document:
{text}"""
