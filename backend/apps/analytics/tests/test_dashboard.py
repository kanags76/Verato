"""Dashboard endpoint tests for Week 4."""
import pytest
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User
from apps.commitments.models import Commitment
from apps.meetings.models import Meeting


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def user(org):
    return User.objects.create_user(username='cos', password='pass', organisation=org)


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Test Meeting', occurred_at=timezone.now(),
    )


def make_commitment(org, meeting, status=Commitment.Status.ACTIVE, risk_score=0.0, deadline=None):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='x', confidence=0.9,
        status=status, risk_score=risk_score, deadline=deadline,
    )


@pytest.mark.django_db
class TestDashboard:
    def test_returns_200(self, client):
        resp = client.get('/api/v1/dashboard/')
        assert resp.status_code == 200

    def test_response_has_expected_keys(self, client):
        resp = client.get('/api/v1/dashboard/')
        assert set(resp.data.keys()) == {'overdue', 'at_risk', 'on_track', 'total_active'}

    def test_empty_org_returns_zeros(self, client):
        resp = client.get('/api/v1/dashboard/')
        assert resp.data == {'overdue': 0, 'at_risk': 0, 'on_track': 0, 'total_active': 0}

    def test_total_active_excludes_closed(self, client, org, meeting):
        make_commitment(org, meeting, status=Commitment.Status.ACTIVE)
        make_commitment(org, meeting, status=Commitment.Status.AT_RISK)
        make_commitment(org, meeting, status=Commitment.Status.DELIVERED)   # excluded
        make_commitment(org, meeting, status=Commitment.Status.CANCELLED)   # excluded
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['total_active'] == 2

    def test_pending_review_counted_in_total_active(self, client, org, meeting):
        make_commitment(org, meeting, status=Commitment.Status.PENDING_REVIEW)
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['total_active'] == 1

    def test_overdue_past_deadline(self, client, org, meeting):
        yesterday = date.today() - timedelta(days=1)
        tomorrow  = date.today() + timedelta(days=1)
        make_commitment(org, meeting, deadline=yesterday)
        make_commitment(org, meeting, deadline=tomorrow)
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['overdue'] == 1

    def test_overdue_no_deadline_not_counted(self, client, org, meeting):
        make_commitment(org, meeting, deadline=None)
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['overdue'] == 0

    def test_at_risk_high_score_future_deadline(self, client, org, meeting):
        tomorrow = date.today() + timedelta(days=1)
        make_commitment(org, meeting, risk_score=0.8, deadline=tomorrow)
        make_commitment(org, meeting, risk_score=0.3, deadline=tomorrow)
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['at_risk'] == 1

    def test_on_track_low_risk_score(self, client, org, meeting):
        make_commitment(org, meeting, risk_score=0.2)
        make_commitment(org, meeting, risk_score=0.9)
        resp = client.get('/api/v1/dashboard/')
        assert resp.data['on_track'] == 1

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get('/api/v1/dashboard/')
        assert resp.status_code == 401
