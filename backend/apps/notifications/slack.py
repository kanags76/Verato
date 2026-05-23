"""
Slack client wrapper and message builders.
All calls are no-ops when SLACK_BOT_TOKEN is empty (local dev / test).
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_NUDGE_HEADERS = {
    'first_reminder':  '📅 *Reminder* — upcoming deadline',
    'second_reminder': '⏰ *Heads up* — deadline approaching',
    'overdue_1':       '⚠️ *Overdue* — was due yesterday',
    'overdue_2':       '🔴 *Overdue* — 2 days past deadline',
    'overdue_3':       '🚨 *Overdue* — 3 days past deadline',
}


def _get_client(org=None):
    """
    Return a Slack WebClient.
    Prefers the per-org token stored in org.settings['slack_token'] (from OAuth).
    Falls back to the global SLACK_BOT_TOKEN env var for single-workspace setups.
    Returns None when no token is available.
    """
    token = None
    if org is not None:
        token = (org.settings or {}).get('slack_token', '')
    if not token:
        token = getattr(settings, 'SLACK_BOT_TOKEN', '')
    if not token:
        return None
    from slack_sdk import WebClient
    return WebClient(token=token)


def send_nudge_dm(slack_user_id: str, commitment, nudge_type: str = 'first_reminder') -> str | None:
    """
    Send a nudge DM to the commitment owner.
    nudge_type controls the header text. Returns Slack channel id or None.
    """
    org = getattr(commitment, 'organisation', None)
    client = _get_client(org=org)
    if client is None:
        logger.info("Slack not configured — skipping nudge for commitment %s", commitment.id)
        return None

    deadline_str = commitment.deadline.strftime('%-d %b %Y') if commitment.deadline else 'no deadline'
    header = _NUDGE_HEADERS.get(nudge_type, '📋 *Commitment reminder*')

    blocks = [
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"{header}\n*{commitment.normalised_text}*\nDeadline: {deadline_str}",
            },
        },
        {
            'type': 'actions',
            'block_id': f'nudge_{commitment.id}',
            'elements': [
                {
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': '✅ Done'},
                    'style': 'primary',
                    'action_id': 'nudge_done',
                    'value': str(commitment.id),
                },
                {
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': '⏰ Need more time'},
                    'action_id': 'nudge_delayed',
                    'value': str(commitment.id),
                },
                {
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': '🚫 Blocked'},
                    'style': 'danger',
                    'action_id': 'nudge_blocked',
                    'value': str(commitment.id),
                },
            ],
        },
    ]

    try:
        response = client.chat_postMessage(channel=slack_user_id, blocks=blocks)
        return response['channel']
    except Exception as exc:
        logger.error("Slack nudge DM failed for %s: %s", slack_user_id, exc)
        return None


def send_cos_overdue_alert(commitment, cos_slack_user_id: str) -> None:
    """Alert the CoS when a commitment becomes overdue."""
    org = getattr(commitment, 'organisation', None)
    client = _get_client(org=org)
    if client is None:
        return

    owner_name = commitment.owner.name if commitment.owner else 'Unassigned'
    deadline_str = commitment.deadline.strftime('%-d %b %Y') if commitment.deadline else 'none'

    try:
        client.chat_postMessage(
            channel=cos_slack_user_id,
            blocks=[
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': (
                            f"🚨 *Overdue commitment — action required*\n"
                            f"*{commitment.normalised_text}*\n"
                            f"Owner: {owner_name} | Deadline: {deadline_str}"
                        ),
                    },
                },
            ],
        )
    except Exception as exc:
        logger.error("CoS overdue alert failed: %s", exc)


def notify_cos_escalation(commitment, cos_slack_user_id: str):
    """Notify the CoS that a commitment has auto-escalated (legacy — kept for risk.py)."""
    send_cos_overdue_alert(commitment, cos_slack_user_id)
