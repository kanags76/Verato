"""Tests for commitment_count + pending_count on MeetingSerializer."""
import pytest
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
        organisation=org, title='Weekly Sync', occurred_at=timezone.now(),
    )


def _make_commitment(org, meeting, status=Commitment.Status.PENDING_REVIEW):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='x', confidence=0.9,
        status=status,
    )


@pytest.mark.django_db
class TestMeetingCommitmentCounts:
    def test_commitment_count_zero_on_new_meeting(self, client, meeting):
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.status_code == 200
        assert resp.data['commitment_count'] == 0
        assert resp.data['pending_count'] == 0

    def test_commitment_count_includes_all_statuses(self, client, org, meeting):
        _make_commitment(org, meeting, Commitment.Status.PENDING_REVIEW)
        _make_commitment(org, meeting, Commitment.Status.ACTIVE)
        _make_commitment(org, meeting, Commitment.Status.DELIVERED)
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.data['commitment_count'] == 3

    def test_pending_count_only_counts_pending_review(self, client, org, meeting):
        _make_commitment(org, meeting, Commitment.Status.PENDING_REVIEW)
        _make_commitment(org, meeting, Commitment.Status.PENDING_REVIEW)
        _make_commitment(org, meeting, Commitment.Status.ACTIVE)
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.data['pending_count'] == 2

    def test_counts_in_list_endpoint(self, client, org, meeting):
        _make_commitment(org, meeting, Commitment.Status.PENDING_REVIEW)
        resp = client.get('/api/v1/meetings/')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        row = next(m for m in results if str(m['id']) == str(meeting.id))
        assert row['commitment_count'] == 1
        assert row['pending_count'] == 1

    def test_pending_count_zero_after_all_confirmed(self, client, org, meeting):
        _make_commitment(org, meeting, Commitment.Status.ACTIVE)
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.data['pending_count'] == 0
