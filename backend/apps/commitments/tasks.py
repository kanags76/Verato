import logging

from celery import shared_task
from django.utils import timezone

from .models import Commitment, EscalationEvent
from .risk import compute_risk_score, score_to_status

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = [
    Commitment.Status.ACTIVE,
    Commitment.Status.AT_RISK,
    Commitment.Status.ESCALATED,
    Commitment.Status.PENDING_REVIEW,
]


@shared_task
def recompute_risk_scores():
    """
    Recompute risk scores for all open commitments and auto-transition status.
    Runs every 24h via Celery Beat. Creates EscalationEvent when auto-escalating.
    """
    qs = (
        Commitment.objects
        .filter(status__in=_ACTIVE_STATUSES)
        .select_related('owner', 'organisation')
    )

    updated = escalated = 0
    for commitment in qs:
        new_score = compute_risk_score(commitment)
        new_status = score_to_status(new_score, commitment.deadline, commitment.status)

        fields = ['risk_score', 'updated_at']
        commitment.risk_score = new_score

        auto_escalated = (
            new_status == Commitment.Status.ESCALATED
            and commitment.status != Commitment.Status.ESCALATED
        )

        if new_status != commitment.status:
            commitment.status = new_status
            fields.append('status')

        commitment.save(update_fields=fields)
        updated += 1

        if auto_escalated:
            EscalationEvent.objects.create(
                commitment=commitment,
                method=EscalationEvent.Method.AUTO,
            )
            escalated += 1

    logger.info(
        "recompute_risk_scores: %d commitments updated, %d auto-escalated",
        updated, escalated,
    )
    return {'updated': updated, 'escalated': escalated}
