"""Unit tests for compute_risk_score() and score_to_status()."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from apps.commitments.risk import compute_risk_score, score_to_status


def _make_commitment(deadline=None, delivery_rate=1.0, updated_days_ago=0, owner=True):
    """Build a minimal commitment-like object without hitting the DB."""
    from types import SimpleNamespace
    from django.utils import timezone

    owner_obj = SimpleNamespace(delivery_rate=delivery_rate) if owner else None
    updated_at = timezone.now() - timedelta(days=updated_days_ago)
    return SimpleNamespace(
        deadline=deadline,
        owner=owner_obj,
        updated_at=updated_at,
    )


# ── compute_risk_score ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestComputeRiskScore:
    def test_overdue_perfect_owner_is_high(self):
        yesterday = date.today() - timedelta(days=1)
        c = _make_commitment(deadline=yesterday, delivery_rate=1.0, updated_days_ago=0)
        score = compute_risk_score(c)
        assert score >= 0.50  # overdue alone drives time_score=1.0 × 0.50

    def test_comfortable_deadline_good_owner_is_low(self):
        far_future = date.today() + timedelta(days=30)
        c = _make_commitment(deadline=far_future, delivery_rate=1.0, updated_days_ago=1)
        score = compute_risk_score(c)
        assert score < 0.20

    def test_no_deadline_moderate_risk(self):
        c = _make_commitment(deadline=None, delivery_rate=1.0, updated_days_ago=0)
        score = compute_risk_score(c)
        assert 0.10 < score < 0.50

    def test_no_owner_adds_moderate_risk(self):
        far = date.today() + timedelta(days=30)
        c_no_owner  = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=0, owner=False)
        c_good_owner = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=0)
        assert compute_risk_score(c_no_owner) > compute_risk_score(c_good_owner)

    def test_bad_owner_raises_score(self):
        far = date.today() + timedelta(days=30)
        c_bad  = _make_commitment(deadline=far, delivery_rate=0.2, updated_days_ago=0)
        c_good = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=0)
        assert compute_risk_score(c_bad) > compute_risk_score(c_good)

    def test_stale_commitment_higher_recency_risk(self):
        far = date.today() + timedelta(days=30)
        c_fresh = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=0)
        c_stale = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=10)
        assert compute_risk_score(c_stale) > compute_risk_score(c_fresh)

    def test_score_capped_at_one(self):
        yesterday = date.today() - timedelta(days=1)
        c = _make_commitment(deadline=yesterday, delivery_rate=0.0, updated_days_ago=30)
        assert compute_risk_score(c) <= 1.0

    def test_score_non_negative(self):
        far = date.today() + timedelta(days=60)
        c = _make_commitment(deadline=far, delivery_rate=1.0, updated_days_ago=0)
        assert compute_risk_score(c) >= 0.0

    def test_due_today_is_very_high(self):
        c = _make_commitment(deadline=date.today(), delivery_rate=1.0, updated_days_ago=0)
        score = compute_risk_score(c)
        assert score >= 0.45  # time_score=0.95 × 0.50

    def test_due_in_two_days_is_elevated(self):
        soon = date.today() + timedelta(days=2)
        c = _make_commitment(deadline=soon, delivery_rate=1.0, updated_days_ago=0)
        score = compute_risk_score(c)
        assert score >= 0.30


# ── score_to_status ───────────────────────────────────────────────────────────

class TestScoreToStatus:
    def test_overdue_always_escalates(self):
        yesterday = date.today() - timedelta(days=1)
        assert score_to_status(0.0, yesterday, 'active') == 'escalated'

    def test_high_score_escalates(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.95, far, 'active') == 'escalated'

    def test_medium_score_at_risk(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.75, far, 'active') == 'at_risk'

    def test_low_score_stays_active(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.20, far, 'active') == 'active'

    def test_recovering_from_at_risk(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.20, far, 'at_risk') == 'active'

    def test_recovering_from_escalated(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.20, far, 'escalated') == 'active'

    def test_closed_statuses_unchanged(self):
        far = date.today() + timedelta(days=30)
        for s in ('delivered', 'deferred', 'cancelled'):
            assert score_to_status(0.99, far, s) == s

    def test_no_deadline_low_score_stays(self):
        assert score_to_status(0.20, None, 'active') == 'active'

    def test_boundary_at_0_70_is_at_risk(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.70, far, 'active') == 'at_risk'

    def test_boundary_at_0_90_is_escalated(self):
        far = date.today() + timedelta(days=30)
        assert score_to_status(0.90, far, 'active') == 'escalated'
