"""
Gmail API helper. Sends nudge emails and polls reply threads for owner responses.
Tokens are stored per-org in org.settings. Access tokens are refreshed automatically.
"""
import base64
import email as email_lib
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

logger = logging.getLogger(__name__)

_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


def _get_service(org):
    """Return an authenticated Gmail API service for the org, or None."""
    s = org.settings or {}
    refresh_token = s.get('gmail_refresh_token')
    if not refresh_token:
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials(
            token         = s.get('gmail_access_token'),
            refresh_token = refresh_token,
            token_uri     = 'https://oauth2.googleapis.com/token',
            client_id     = settings.GOOGLE_CLIENT_ID,
            client_secret = settings.GOOGLE_CLIENT_SECRET,
            scopes        = _SCOPES,
        )
        if creds.expired:
            creds.refresh(Request())
            # Persist refreshed token
            org.settings['gmail_access_token'] = creds.token
            org.save(update_fields=['settings'])

        return build('gmail', 'v1', credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error("Gmail service init failed for org %s: %s", org.slug, exc)
        return None


def send_nudge_email(org, to_email: str, owner_name: str, commitment, note: str = '') -> str | None:
    """
    Send a nudge email from the CoS's Gmail account to the owner.
    Returns the Gmail thread_id on success, None on failure.
    """
    service = _get_service(org)
    if service is None:
        logger.info("Gmail not connected for org %s — skipping email nudge", org.slug)
        return None

    deadline_str = commitment.deadline.strftime('%-d %b %Y') if commitment.deadline else 'not set'
    from_email   = (org.settings or {}).get('gmail_email', '')

    subject = f'[Verato] Commitment reminder — due {deadline_str}'
    body    = f"""Hi {owner_name},

This is a reminder about the following commitment:

"{commitment.normalised_text}"

Deadline: {deadline_str}
"""
    if note:
        body += f'\nNote from your team: {note}\n'

    body += f"""
Please reply to this email with a quick update, or log it directly in Verato.

---
ref:{commitment.id}
"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['To']      = to_email
    if from_email:
        msg['From'] = from_email
    msg.attach(MIMEText(body, 'plain'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        result = service.users().messages().send(
            userId='me', body={'raw': raw}
        ).execute()
        return result.get('threadId')
    except Exception as exc:
        logger.error("Gmail send failed for org %s to %s: %s", org.slug, to_email, exc)
        return None


def poll_reply_threads(org) -> list[dict]:
    """
    Check all open NudgeLog entries with a gmail_thread_id for replies.
    Returns list of dicts: {nudge_log, reply_body, message_id}
    """
    from .models import NudgeLog

    service = _get_service(org)
    if service is None:
        return []

    # Find nudge logs with gmail thread IDs from the last 30 days
    from django.utils import timezone
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(days=30)

    nudge_logs = list(
        NudgeLog.objects
        .filter(commitment__organisation=org)
        .filter(gmail_thread_id__gt='')
        .filter(nudged_at__gte=cutoff)
        .select_related('commitment', 'person')
    )

    replies = []
    for nl in nudge_logs:
        try:
            thread = service.users().threads().get(
                userId='me', id=nl.gmail_thread_id, format='full'
            ).execute()
            messages = thread.get('messages', [])
            if len(messages) <= 1:
                continue  # no reply yet

            # Get the latest message that isn't from us
            our_sent_id = messages[0].get('id')
            reply_messages = [m for m in messages[1:] if m.get('id') != our_sent_id]
            if not reply_messages:
                continue

            latest     = reply_messages[-1]
            message_id = latest.get('id')
            if message_id and message_id == nl.last_reply_message_id:
                continue  # already processed this reply
            reply_body = _extract_body(latest)
            if reply_body:
                replies.append({
                    'nudge_log':  nl,
                    'reply_body': reply_body,
                    'message_id': message_id,
                })
        except Exception as exc:
            logger.warning("Gmail thread fetch failed %s: %s", nl.gmail_thread_id, exc)

    return replies


def _extract_body(message: dict) -> str:
    """Extract plain text body from a Gmail message dict."""
    try:
        payload = message.get('payload', {})
        parts   = payload.get('parts', [])

        # Single part message
        if not parts:
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

        # Multipart — prefer text/plain
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
    except Exception:
        pass
    return ''


def _load_prompt(name: str, fallback: str) -> str:
    try:
        from apps.prompts.models import Prompt
        return Prompt.objects.get(name=name).content
    except Exception:
        return fallback


_GMAIL_REPLY_PARSE_FALLBACK = (
    'An owner replied to a commitment reminder email. Extract a structured update.\n\n'
    'COMMITMENT: {commitment_text}\nDEADLINE: {deadline_str}\n\nREPLY EMAIL:\n{reply_body}\n\n'
    'Return JSON only (no markdown):\n'
    '{{"intent": "done"|"active"|"deferred"|"blocked"|"no_update", '
    '"note": "1-2 sentence summary", "suggested_deadline": "YYYY-MM-DD or null"}}'
)


def parse_reply_with_gemini(
    commitment_text: str,
    deadline_str: str,
    reply_body: str,
    log_context: dict | None = None,
) -> dict:
    """
    Use Gemini to extract intent + summary from an email reply.
    Returns: { intent, note, suggested_deadline }
    Prompt is loaded from the DB (prompts.gmail_reply_parse) so it can be edited in admin.
    """
    from apps.prompts.logger import call_gemini
    try:
        template = _load_prompt('gmail_reply_parse', _GMAIL_REPLY_PARSE_FALLBACK)
        prompt = template.format(
            commitment_text=commitment_text,
            deadline_str=deadline_str,
            reply_body=reply_body[:2000],
        )
        raw = call_gemini(prompt, 'gmail_reply_parse', **(log_context or {}))
        if not raw:
            return {'intent': 'no_update', 'note': reply_body[:200], 'suggested_deadline': None}
        text = raw.strip()
        if '```' in text:
            parts = text.split('```')
            for part in parts:
                candidate = part.lstrip('json').strip()
                if candidate.startswith('{'):
                    text = candidate
                    break
        return json.loads(text.strip())
    except Exception as exc:
        logger.error("Gemini reply parse failed: %s", exc)
        return {'intent': 'no_update', 'note': reply_body[:200], 'suggested_deadline': None}
