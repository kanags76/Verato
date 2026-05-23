import logging
from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.commitments.models import Commitment, CommitmentEvent
from .models import NudgeLog
from .slack import send_nudge_dm, send_cos_overdue_alert

logger = logging.getLogger(__name__)

_SKIP_STATUSES = {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}


@shared_task
def send_deadline_nudges():
    """
    Daily nudge engine (runs 09:00 UTC via Celery Beat).

    Per org nudge schedule (configured via GET/PATCH /api/v1/nudge-settings/):
      - FIRST_REMINDER:  nudge_first_days_before days before deadline (default 2)
      - SECOND_REMINDER: nudge_second_hours_before / 24 days before deadline (default 48h)
      - OVERDUE_1/2/3:   1, 2, 3 days after deadline
      - ESCALATION:      CoS alerted on day +1

    Skip: no owner slack_user_id, DELIVERED/CANCELLED status, nudge_type already logged.
    """
    from apps.accounts.models import Organisation

    today = date.today()
    sent = escalated = skipped = 0

    for org in Organisation.objects.all():
        org_settings = org.settings or {}
        if not org_settings.get('slack_token'):
            continue
        if not org_settings.get('nudge_enabled', False):
            continue

        first_days   = int(org_settings.get('nudge_first_days_before', 2))
        second_hours = int(org_settings.get('nudge_second_hours_before', 48))
        second_days  = second_hours // 24
        cos_slack_id = _get_cos_slack_id(org)

        commitments = (
            Commitment.objects
            .filter(organisation=org, deadline__isnull=False)
            .exclude(status__in=_SKIP_STATUSES)
            .select_related('owner', 'organisation')
        )

        for commitment in commitments:
            days_until = (commitment.deadline - today).days  # negative when overdue
            days_over  = -days_until                          # positive when overdue

            due_types = _due_nudge_types(days_until, days_over, first_days, second_days, commitment)

            if not due_types:
                continue

            owner = commitment.owner
            if not owner or not owner.slack_user_id:
                skipped += 1
                continue

            for nudge_type in due_types:
                _, created = NudgeLog.objects.get_or_create(
                    commitment=commitment,
                    nudge_type=nudge_type,
                    defaults={'person': owner, 'channel': ''},
                )
                if not created:
                    continue  # already sent for this type

                channel = send_nudge_dm(owner.slack_user_id, commitment, nudge_type)
                if channel:
                    NudgeLog.objects.filter(
                        commitment=commitment, nudge_type=nudge_type
                    ).update(channel=channel)

                CommitmentEvent.objects.create(
                    commitment=commitment,
                    event_type=CommitmentEvent.EventType.NUDGED,
                    note=f'Slack nudge sent ({nudge_type}) to {owner.name}',
                )
                sent += 1

                # On first overdue day alert CoS (once per commitment)
                if nudge_type == NudgeLog.NudgeType.OVERDUE_1 and cos_slack_id:
                    _, cos_created = NudgeLog.objects.get_or_create(
                        commitment=commitment,
                        nudge_type=NudgeLog.NudgeType.ESCALATION,
                        defaults={'person': None, 'channel': ''},
                    )
                    if cos_created:
                        send_cos_overdue_alert(commitment, cos_slack_id)
                        escalated += 1

    logger.info(
        "send_deadline_nudges: %d nudges sent, %d CoS escalations, %d skipped (no Slack ID)",
        sent, escalated, skipped,
    )
    return {'sent': sent, 'escalated': escalated, 'skipped': skipped}


def _due_nudge_types(days_until, days_over, first_days, second_days, commitment):
    """Return list of NudgeType values due today for this commitment."""
    due = []

    if days_until == first_days:
        due.append(NudgeLog.NudgeType.FIRST_REMINDER)

    if days_until == second_days:
        if second_days != first_days:
            due.append(NudgeLog.NudgeType.SECOND_REMINDER)
        else:
            # Same day as FIRST — only add SECOND if FIRST already sent previously
            if NudgeLog.objects.filter(
                commitment=commitment, nudge_type=NudgeLog.NudgeType.FIRST_REMINDER
            ).exists():
                due.append(NudgeLog.NudgeType.SECOND_REMINDER)

    overdue_map = {1: NudgeLog.NudgeType.OVERDUE_1, 2: NudgeLog.NudgeType.OVERDUE_2, 3: NudgeLog.NudgeType.OVERDUE_3}
    if days_over in overdue_map:
        due.append(overdue_map[days_over])

    return due


def _get_cos_slack_id(org) -> str | None:
    from apps.accounts.models import User
    try:
        admin = (
            User.objects
            .filter(organisation=org, is_org_admin=True)
            .select_related('person')
            .first()
        )
        if admin and hasattr(admin, 'person') and admin.person.slack_user_id:
            return admin.person.slack_user_id
    except Exception:
        pass
    return None


@shared_task
def send_weekly_digest():
    """Monday 07:00 UTC — weekly commitment digest email."""
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
        if not commitments:
            continue

        overdue  = [c for c in commitments if c.deadline and c.deadline < today]
        at_risk  = [c for c in commitments if c.risk_score >= 0.7 and not (c.deadline and c.deadline < today)]
        on_track = [c for c in commitments if c.risk_score < 0.7 and not (c.deadline and c.deadline < today)]

        intro = _generate_digest_intro(org.name, overdue, at_risk, on_track)
        context = {'org_name': org.name, 'intro': intro, 'overdue': overdue,
                   'at_risk': at_risk, 'on_track': on_track, 'today': today}
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


def _generate_digest_intro(org_name, overdue, at_risk, on_track) -> str:
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(settings.GEMINI_EXTRACTION_MODEL)
        prompt = (
            f"Write a 2-3 sentence executive summary for {org_name}'s weekly commitment digest. "
            f"{len(overdue)} overdue, {len(at_risk)} at-risk, {len(on_track)} on-track. "
            f"Be concise and action-oriented. Plain text only."
        )
        return model.generate_content(prompt).text.strip()
    except Exception as exc:
        logger.warning("Gemini digest intro failed: %s", exc)
        return (
            f"Here is your weekly commitment summary for {org_name}. "
            f"{len(overdue)} overdue, {len(at_risk)} at risk, {len(on_track)} on track."
        )
