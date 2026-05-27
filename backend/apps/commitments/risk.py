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


def compute_risk_breakdown(commitment) -> dict:
    """
    Same logic as compute_risk_score but returns each component separately
    for display in the commitment detail view.
    """
    today = date.today()

    # Component 1: deadline proximity (50%)
    if commitment.deadline:
        days = (commitment.deadline - today).days
        if days < 0:
            time_score = 1.0
            deadline_label = f"Overdue by {-days} day{'s' if -days != 1 else ''}"
        elif days == 0:
            time_score = 0.95
            deadline_label = "Due today"
        elif days == 1:
            time_score = 0.85
            deadline_label = "Due tomorrow"
        elif days <= 3:
            time_score = 0.65
            deadline_label = f"Due in {days} days"
        elif days <= 7:
            time_score = 0.40
            deadline_label = f"Due in {days} days"
        elif days <= 14:
            time_score = 0.20
            deadline_label = f"Due in {days} days"
        else:
            time_score = 0.05
            deadline_label = f"Due in {days} days"
    else:
        time_score = 0.30
        deadline_label = "No deadline set"

    # Component 2: owner delivery rate (35%)
    if commitment.owner:
        delivery_rate = commitment.owner.delivery_rate
        owner_risk = 1.0 - delivery_rate
        owner_label = f"{int(delivery_rate * 100)}% historical delivery rate"
    else:
        owner_risk = 0.50
        delivery_rate = None
        owner_label = "No owner assigned"

    # Component 3: update recency (15%)
    if commitment.updated_at:
        from django.utils import timezone as tz
        days_since = (tz.now() - commitment.updated_at).days
        if days_since > 7:
            recency_risk = 0.80
            recency_label = f"No activity in {days_since} days"
        elif days_since > 3:
            recency_risk = 0.40
            recency_label = f"Last activity {days_since} days ago"
        else:
            recency_risk = 0.10
            recency_label = "Active recently"
    else:
        recency_risk = 0.50
        recency_label = "No activity recorded"

    total = min(time_score * 0.50 + owner_risk * 0.35 + recency_risk * 0.15, 1.0)

    return {
        'total': round(total, 3),
        'deadline_proximity': {
            'raw_score':    round(time_score, 2),
            'weight':       0.50,
            'contribution': round(time_score * 0.50, 3),
            'label':        deadline_label,
        },
        'owner_track_record': {
            'raw_score':    round(owner_risk, 2),
            'weight':       0.35,
            'contribution': round(owner_risk * 0.35, 3),
            'label':        owner_label,
            'delivery_rate': delivery_rate,
        },
        'update_recency': {
            'raw_score':    round(recency_risk, 2),
            'weight':       0.15,
            'contribution': round(recency_risk * 0.15, 3),
            'label':        recency_label,
        },
    }


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
