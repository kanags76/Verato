import logging
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.commitments.models import Commitment
from .models import NudgeLog
from .slack import send_nudge_dm

logger = logging.getLogger(__name__)

_NUDGE_WINDOW_HOURS = 48
_NUDGE_COOLDOWN_HOURS = 20  # don't re-nudge within this window


@shared_task
def send_deadline_nudges():
    """
    Find commitments due within 48h whose owner has a Slack user id.
    Send a DM if we haven't nudged this commitment in the last 20h.
    Runs daily at 09:00 UTC via Celery Beat.
    """
    cutoff = date.today() + timedelta(hours=_NUDGE_WINDOW_HOURS)
    cooldown_after = timezone.now() - timedelta(hours=_NUDGE_COOLDOWN_HOURS)

    candidates = (
        Commitment.objects
        .filter(
            status__in=[Commitment.Status.ACTIVE, Commitment.Status.AT_RISK],
            deadline__lte=cutoff,
            deadline__gte=date.today(),
            owner__slack_user_id__gt='',
        )
        .select_related('owner')
        .exclude(nudges__nudged_at__gte=cooldown_after)
    )

    sent = 0
    for commitment in candidates:
        channel = send_nudge_dm(commitment.owner.slack_user_id, commitment)
        NudgeLog.objects.create(commitment=commitment, channel=channel or '')
        sent += 1

    logger.info("send_deadline_nudges: %d nudges sent", sent)
    return {'sent': sent}


@shared_task
def send_weekly_digest():
    """
    Monday 07:00 UTC — build and send the weekly commitment digest email.
    Sections: Overdue / At Risk / On Track.
    Gemini generates the opening paragraph.
    Sends to all users with an email address in the org.
    """
    from apps.accounts.models import User

    today = date.today()
    active_statuses = [
        Commitment.Status.ACTIVE,
        Commitment.Status.AT_RISK,
        Commitment.Status.ESCALATED,
        Commitment.Status.PENDING_REVIEW,
    ]

    orgs_sent = 0
    for org in _iter_orgs_with_email_users():
        commitments = list(
            Commitment.objects
            .filter(organisation=org, status__in=active_statuses)
            .select_related('owner')
            .order_by('deadline', '-risk_score')
        )

        overdue  = [c for c in commitments if c.deadline and c.deadline < today]
        at_risk  = [c for c in commitments if c.risk_score >= 0.7 and not (c.deadline and c.deadline < today)]
        on_track = [c for c in commitments if c.risk_score < 0.7 and not (c.deadline and c.deadline < today)]

        intro = _generate_digest_intro(org.name, overdue, at_risk, on_track)

        context = {
            'org_name': org.name,
            'intro':    intro,
            'overdue':  overdue,
            'at_risk':  at_risk,
            'on_track': on_track,
            'today':    today,
        }
        html_body = render_to_string('emails/weekly_digest.html', context)
        text_body = (
            f"Weekly digest for {org.name}\n\n{intro}\n\n"
            f"Overdue: {len(overdue)} | At risk: {len(at_risk)} | On track: {len(on_track)}"
        )

        recipients = list(
            User.objects.filter(organisation=org, email__gt='').values_list('email', flat=True)
        )
        if not recipients:
            continue

        if not commitments:
            continue

        msg = EmailMultiAlternatives(
            subject=f"Verato weekly digest — {today.strftime('%d %b %Y')}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        msg.attach_alternative(html_body, 'text/html')

        try:
            msg.send()
            orgs_sent += 1
        except Exception as exc:
            logger.error("Weekly digest failed for org %s: %s", org.slug, exc)

    logger.info("send_weekly_digest: sent for %d orgs", orgs_sent)
    return {'orgs_sent': orgs_sent}


def _iter_orgs_with_email_users():
    from apps.accounts.models import Organisation
    return Organisation.objects.filter(users__email__gt='').distinct()


def _generate_digest_intro(org_name: str, overdue, at_risk, on_track) -> str:
    """Call Gemini Flash for a 2-3 sentence digest intro. Falls back to a plain string."""
    try:
        from django.conf import settings as s
        import google.generativeai as genai
        model = genai.GenerativeModel(s.GEMINI_EXTRACTION_MODEL)
        prompt = (
            f"Write a 2-3 sentence executive summary for {org_name}'s weekly commitment digest. "
            f"There are {len(overdue)} overdue, {len(at_risk)} at-risk, and {len(on_track)} on-track "
            f"commitments. Be concise and action-oriented. Plain text only."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        logger.warning("Gemini digest intro failed: %s", exc)
        return (
            f"Here is your weekly commitment summary for {org_name}. "
            f"{len(overdue)} commitments are overdue, {len(at_risk)} are at risk, "
            f"and {len(on_track)} are on track."
        )
