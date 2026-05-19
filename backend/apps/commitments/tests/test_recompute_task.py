"""Tests for recompute_risk_scores Celery task (Week 5)."""
import pytest
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User
from apps.commitments.models import Commitment, EscalationEvent
from apps.commitments.tasks import recompute_risk_scores
from apps.meetings.models import Meeting


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Test Meeting', occurred_at=timezone.now(),
    )


def make_commitment(org, meeting, status=Commitment.Status.ACTIVE, deadline=None, risk_score=0.0):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='x', confidence=0.9,
        status=status, risk_score=risk_score, deadline=deadline,
    )


# ── status transitions ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecomputeStatusTransitions:
    def test_overdue_active_becomes_escalated(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(org, meeting, deadline=yesterday)
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status == Commitment.Status.ESCALATED

    def test_far_future_deadline_stays_active(self, org, meeting):
        far = date.today() + timedelta(days=60)
        c = make_commitment(org, meeting, deadline=far)
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status == Commitment.Status.ACTIVE

    def test_near_deadline_bad_owner_becomes_at_risk(self, org, meeting):
        from apps.accounts.models import Person
        # 1-day deadline + low delivery rate owner → score > 0.70 → AT_RISK
        bad_owner = Person.objects.create(organisation=org, name='Unreliable', delivery_rate=0.0)
        tomorrow = date.today() + timedelta(days=1)
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
            status=Commitment.Status.ACTIVE, deadline=tomorrow, owner=bad_owner,
        )
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status in {Commitment.Status.AT_RISK, Commitment.Status.ESCALATED}

    def test_delivered_not_touched(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(
            org, meeting,
            status=Commitment.Status.DELIVERED,
            deadline=yesterday,
        )
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status == Commitment.Status.DELIVERED

    def test_cancelled_not_touched(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(
            org, meeting,
            status=Commitment.Status.CANCELLED,
            deadline=yesterday,
        )
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status == Commitment.Status.CANCELLED

    def test_deferred_not_touched(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(
            org, meeting,
            status=Commitment.Status.DEFERRED,
            deadline=yesterday,
        )
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.status == Commitment.Status.DEFERRED


# ── risk score written ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecomputeRiskScoreWritten:
    def test_risk_score_updated(self, org, meeting):
        far = date.today() + timedelta(days=60)
        c = make_commitment(org, meeting, deadline=far, risk_score=0.0)
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.risk_score > 0.0

    def test_overdue_risk_score_is_high(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(org, meeting, deadline=yesterday)
        recompute_risk_scores.apply(throw=True)
        c.refresh_from_db()
        assert c.risk_score >= 0.50


# ── EscalationEvent creation ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecomputeAutoEscalation:
    def test_auto_escalation_creates_event(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(org, meeting, deadline=yesterday)
        recompute_risk_scores.apply(throw=True)
        assert EscalationEvent.objects.filter(commitment=c, method=EscalationEvent.Method.AUTO).exists()

    def test_already_escalated_no_duplicate_event(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        c = make_commitment(
            org, meeting,
            status=Commitment.Status.ESCALATED,
            deadline=yesterday,
        )
        recompute_risk_scores.apply(throw=True)
        assert EscalationEvent.objects.filter(commitment=c).count() == 0

    def test_non_overdue_no_auto_escalation_event(self, org, meeting):
        far = date.today() + timedelta(days=60)
        c = make_commitment(org, meeting, deadline=far)
        recompute_risk_scores.apply(throw=True)
        assert EscalationEvent.objects.filter(commitment=c).count() == 0


# ── task return value ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecomputeTaskReturnValue:
    def test_returns_updated_count(self, org, meeting):
        make_commitment(org, meeting)
        make_commitment(org, meeting)
        result = recompute_risk_scores.apply(throw=True).get()
        assert result['updated'] == 2

    def test_returns_escalated_count(self, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        make_commitment(org, meeting, deadline=yesterday)
        result = recompute_risk_scores.apply(throw=True).get()
        assert result['escalated'] == 1

    def test_empty_org_returns_zeros(self, org):
        result = recompute_risk_scores.apply(throw=True).get()
        assert result == {'updated': 0, 'escalated': 0}
