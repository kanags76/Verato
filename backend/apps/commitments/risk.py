from datetime import date

from django.utils import timezone


def compute_risk_score(commitment) -> float:
    """
    Returns float 0.0–1.0.
    Above 0.70 → AT_RISK. Above 0.90 → ESCALATED.
    Past deadline + not closed → treated as ESCALATED regardless of score.

    Weights: deadline proximity 50%, owner delivery rate 35%, update recency 15%.
    """
    today = date.today()
    score = 0.0

    # Component 1: deadline proximity (50%)
    if commitment.deadline:
        days = (commitment.deadline - today).days
        if days < 0:
            time_score = 1.0
        elif days == 0:
            time_score = 0.95
        elif days <= 1:
            time_score = 0.85
        elif days <= 3:
            time_score = 0.65
        elif days <= 7:
            time_score = 0.40
        elif days <= 14:
            time_score = 0.20
        else:
            time_score = 0.05
    else:
        time_score = 0.30

    score += time_score * 0.50

    # Component 2: owner delivery rate (35%)
    if commitment.owner:
        owner_risk = 1.0 - commitment.owner.delivery_rate
    else:
        owner_risk = 0.50

    score += owner_risk * 0.35

    # Component 3: update recency (15%)
    if commitment.updated_at:
        days_since = (timezone.now() - commitment.updated_at).days
        if days_since > 7:
            recency_risk = 0.80
        elif days_since > 3:
            recency_risk = 0.40
        else:
            recency_risk = 0.10
    else:
        recency_risk = 0.50

    score += recency_risk * 0.15

    return min(score, 1.0)


def score_to_status(score: float, deadline, current_status: str) -> str:
    """Determine new status from risk score and deadline. Never closes a commitment."""
    today = date.today()
    closed = {'done', 'deferred', 'cancelled'}

    if current_status in closed:
        return current_status

    if deadline and deadline < today:
        return 'escalated'

    if score >= 0.90:
        return 'escalated'
    elif score >= 0.70:
        return 'at_risk'
    elif current_status in {'at_risk', 'escalated'}:
        return 'active'
    else:
        return current_status
