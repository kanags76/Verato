"""
Slack client wrapper and message builders.
All calls are no-ops when SLACK_BOT_TOKEN is empty (local dev / test).
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


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


def send_nudge_dm(slack_user_id: str, commitment) -> str | None:
    """
    Send a deadline nudge DM to the owner.
    Returns the Slack channel id on success, None if Slack is not configured.
    """
    org = getattr(commitment, 'organisation', None)
    client = _get_client(org=org)
    if client is None:
        logger.info("Slack not configured — skipping nudge for commitment %s", commitment.id)
        return None

    deadline_str = commitment.deadline.isoformat() if commitment.deadline else 'no deadline set'
    blocks = [
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    f"*Commitment reminder* — deadline {deadline_str}\n"
                    f"_{commitment.normalised_text}_"
                ),
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
                    'text': {'type': 'plain_text', 'text': '⏰ Delayed'},
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
        logger.error("Slack DM failed for user %s: %s", slack_user_id, exc)
        return None


def notify_cos_escalation(commitment, cos_slack_user_id: str):
    """Notify the CoS that a commitment has auto-escalated."""
    org = getattr(commitment, 'organisation', None)
    client = _get_client(org=org)
    if client is None:
        return

    try:
        client.chat_postMessage(
            channel=cos_slack_user_id,
            text=(
                f"⚠️ *Auto-escalated* — {commitment.normalised_text[:120]}\n"
                f"Owner: {commitment.owner.name if commitment.owner else 'unassigned'} | "
                f"Deadline: {commitment.deadline or 'none'}"
            ),
        )
    except Exception as exc:
        logger.error("CoS escalation notify failed: %s", exc)
