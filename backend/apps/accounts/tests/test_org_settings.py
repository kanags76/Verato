"""Tests for OrgSettingsView (PATCH /orgs/{id}/settings/) and is_first_login on register."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, Person, User


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Acme Corp', slug='acme-corp', plan='team')


@pytest.fixture
def admin_user(org):
    u = User.objects.create_user(
        username='admin@acme.com', email='admin@acme.com',
        password='adminpass1', organisation=org, is_org_admin=True,
    )
    Person.objects.create(organisation=org, user=u, name='Admin', email='admin@acme.com')
    return u


@pytest.fixture
def member_user(org):
    u = User.objects.create_user(
        username='member@acme.com', email='member@acme.com',
        password='pass1234', organisation=org, is_org_admin=False,
    )
    Person.objects.create(organisation=org, user=u, name='Member', email='member@acme.com')
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def member_client(member_user):
    c = APIClient()
    c.force_authenticate(user=member_user)
    return c


def _url(org):
    return f'/api/v1/orgs/{org.id}/settings/'


# ── is_first_login on register ────────────────────────────────────────────────

@pytest.mark.django_db
class TestIsFirstLogin:
    URL = '/api/v1/auth/register/'

    def test_register_returns_is_first_login_true(self):
        api = APIClient()
        resp = api.post(self.URL, {
            'name': 'New User', 'email': 'new@example.com',
            'password': 'securepass', 'plan': 'individual', 'org_name': 'New Co',
        })
        assert resp.status_code == 201
        assert resp.data.get('is_first_login') is True

    def test_register_returns_jwt_tokens(self):
        api = APIClient()
        resp = api.post(self.URL, {
            'name': 'New User', 'email': 'new2@example.com',
            'password': 'securepass', 'plan': 'individual', 'org_name': 'New Co 2',
        })
        assert 'access' in resp.data
        assert 'refresh' in resp.data


# ── OrgSettingsView ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOrgSettings:
    def test_admin_can_update_confidence_threshold(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'confidence_threshold': 0.85}, format='json')
        assert resp.status_code == 200
        assert resp.data['settings']['confidence_threshold'] == 0.85

    def test_admin_can_update_nudge_hours(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'nudge_hours_before': 48}, format='json')
        assert resp.status_code == 200
        assert resp.data['settings']['nudge_hours_before'] == 48

    def test_admin_can_update_digest_schedule(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'digest_day': 'mon', 'digest_hour': 9}, format='json')
        assert resp.status_code == 200
        settings = resp.data['settings']
        assert settings['digest_day'] == 'mon'
        assert settings['digest_hour'] == 9

    def test_settings_are_merged_not_replaced(self, admin_client, org):
        admin_client.patch(_url(org), {'confidence_threshold': 0.7}, format='json')
        admin_client.patch(_url(org), {'nudge_hours_before': 24}, format='json')
        org.refresh_from_db()
        assert org.settings['confidence_threshold'] == 0.7
        assert org.settings['nudge_hours_before'] == 24

    def test_member_cannot_update_settings(self, member_client, org):
        resp = member_client.patch(_url(org), {'confidence_threshold': 0.5}, format='json')
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, org):
        api = APIClient()
        resp = api.patch(_url(org), {'confidence_threshold': 0.5}, format='json')
        assert resp.status_code == 401

    def test_wrong_org_id_returns_404(self, admin_client):
        fake_url = '/api/v1/orgs/00000000-0000-0000-0000-000000000000/settings/'
        resp = admin_client.patch(fake_url, {'confidence_threshold': 0.5}, format='json')
        assert resp.status_code == 404

    def test_confidence_above_1_rejected(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'confidence_threshold': 1.5}, format='json')
        assert resp.status_code == 400

    def test_confidence_below_0_rejected(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'confidence_threshold': -0.1}, format='json')
        assert resp.status_code == 400

    def test_invalid_digest_day_rejected(self, admin_client, org):
        resp = admin_client.patch(_url(org), {'digest_day': 'monday'}, format='json')
        assert resp.status_code == 400

    def test_slack_keys_not_exposed_in_response(self, admin_client, org):
        org.settings['slack_token'] = 'xoxb-secret'
        org.save(update_fields=['settings'])
        resp = admin_client.patch(_url(org), {'nudge_hours_before': 12}, format='json')
        assert 'slack_token' not in resp.data.get('settings', {})
