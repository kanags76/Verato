"""Tests for GET /slack/status/ and POST /slack/test-message/."""
import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, Person, User


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def user(org):
    u = User.objects.create_user(username='cos@test.com', email='cos@test.com',
                                 password='pass', organisation=org)
    Person.objects.create(organisation=org, user=u, name='CoS', email='cos@test.com')
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def connected_org(org):
    org.settings = {
        'slack_token': 'xoxb-test-token',
        'slack_workspace_id': 'T12345',
        'slack_workspace_name': 'Acme Slack',
    }
    org.save(update_fields=['settings'])
    return org


# ── GET /slack/status/ ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSlackStatus:
    URL = '/api/v1/slack/status/'

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(self.URL)
        assert resp.status_code == 401

    def test_not_connected_when_no_token(self, client, org):
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data['connected'] is False
        assert resp.data['workspace_id'] is None

    def test_connected_when_token_present(self, client, connected_org):
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data['connected'] is True
        assert resp.data['workspace_id'] == 'T12345'
        assert resp.data['workspace_name'] == 'Acme Slack'


# ── POST /slack/test-message/ ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestSlackTestMessage:
    URL = '/api/v1/slack/test-message/'

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post(self.URL)
        assert resp.status_code == 401

    def test_no_slack_user_id_returns_400(self, client, connected_org):
        resp = client.post(self.URL)
        assert resp.status_code == 400
        assert 'link-slack' in resp.data['detail']

    def test_slack_not_connected_returns_400(self, client, user):
        person = user.person
        person.slack_user_id = 'U123'
        person.save(update_fields=['slack_user_id'])
        with patch('apps.notifications.slack._get_client', return_value=None):
            resp = client.post(self.URL)
        assert resp.status_code == 400
        assert 'not connected' in resp.data['detail']

    def test_sends_message_when_configured(self, client, connected_org, user):
        person = user.person
        person.slack_user_id = 'U123ABC'
        person.save(update_fields=['slack_user_id'])

        mock_client = MagicMock()
        with patch('apps.notifications.views.slack_test_message.__wrapped__',
                   create=True), \
             patch('apps.notifications.slack._get_client', return_value=mock_client):
            resp = client.post(self.URL)

        assert resp.status_code == 200
        assert resp.data['detail'] == 'Test message sent.'

    def test_slack_failure_returns_502(self, client, connected_org, user):
        person = user.person
        person.slack_user_id = 'U123ABC'
        person.save(update_fields=['slack_user_id'])

        mock_client = MagicMock()
        mock_client.chat_postMessage.side_effect = Exception('Slack error')
        with patch('apps.notifications.slack._get_client', return_value=mock_client):
            resp = client.post(self.URL)

        assert resp.status_code == 502
