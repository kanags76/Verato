"""Tests for Slack action webhook (button clicks from nudge DMs)."""
import json
import pytest
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation
from apps.commitments.models import Commitment
from apps.meetings.models import Meeting

# Bypass Slack signature verification in all tests in this module
pytestmark = pytest.mark.usefixtures('mock_slack_verify')


@pytest.fixture(autouse=True)
def mock_slack_verify():
    with patch('apps.notifications.views._verify_slack_signature', return_value=True):
        yield


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Test Meeting', occurred_at=timezone.now(),
    )


@pytest.fixture
def active_commitment(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='x', confidence=0.9,
        status=Commitment.Status.ACTIVE,
    )


def _payload(action_id, commitment_id):
    return {
        'actions': [{'action_id': action_id, 'value': str(commitment_id)}]
    }


def post_action(client, action_id, commitment_id):
    payload = json.dumps(_payload(action_id, commitment_id))
    return client.post('/api/v1/slack/actions/', data={'payload': payload})


@pytest.mark.django_db
class TestSlackActions:
    def test_done_marks_delivered(self, client, active_commitment):
        resp = post_action(client, 'nudge_done', active_commitment.id)
        assert resp.status_code == 200
        active_commitment.refresh_from_db()
        assert active_commitment.status == Commitment.Status.DELIVERED

    def test_done_sets_resolved_at(self, client, active_commitment):
        post_action(client, 'nudge_done', active_commitment.id)
        active_commitment.refresh_from_db()
        assert active_commitment.resolved_at is not None

    def test_delayed_marks_deferred(self, client, active_commitment):
        resp = post_action(client, 'nudge_delayed', active_commitment.id)
        assert resp.status_code == 200
        active_commitment.refresh_from_db()
        assert active_commitment.status == Commitment.Status.DEFERRED

    def test_blocked_marks_at_risk(self, client, active_commitment):
        resp = post_action(client, 'nudge_blocked', active_commitment.id)
        assert resp.status_code == 200
        active_commitment.refresh_from_db()
        assert active_commitment.status == Commitment.Status.AT_RISK

    def test_unknown_commitment_returns_200(self, client):
        import uuid
        resp = post_action(client, 'nudge_done', uuid.uuid4())
        assert resp.status_code == 200

    def test_already_delivered_not_changed(self, client, org, meeting):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
            status=Commitment.Status.DELIVERED,
        )
        post_action(client, 'nudge_delayed', c.id)
        c.refresh_from_db()
        assert c.status == Commitment.Status.DELIVERED

    def test_empty_payload_returns_200(self, client):
        resp = client.post('/api/v1/slack/actions/', data={'payload': '{}'})
        assert resp.status_code == 200

    def test_get_not_allowed(self, client):
        resp = client.get('/api/v1/slack/actions/')
        assert resp.status_code == 405


@pytest.fixture
def client():
    from django.test import Client
    return Client()
