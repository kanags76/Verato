"""Tests for registration, invite, accept-invite, and link-slack flows."""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

from apps.accounts.models import Invitation, Organisation, Person, User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Acme Corp', slug='acme-corp', plan='team')


@pytest.fixture
def admin_user(org):
    u = User.objects.create_user(
        username='admin@acme.com', email='admin@acme.com',
        password='adminpass1', organisation=org, is_org_admin=True,
    )
    Person.objects.create(organisation=org, user=u, name='Admin User', email='admin@acme.com')
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def member_user(org):
    u = User.objects.create_user(
        username='member@acme.com', email='member@acme.com',
        password='pass1234', organisation=org, is_org_admin=False,
    )
    Person.objects.create(organisation=org, user=u, name='Member', email='member@acme.com')
    return u


@pytest.fixture
def member_client(member_user):
    c = APIClient()
    c.force_authenticate(user=member_user)
    return c


# ── Email login ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmailLogin:
    URL = '/api/v1/auth/token/'

    def test_login_with_email_returns_tokens(self, api, admin_user):
        resp = api.post(self.URL, {'email': admin_user.email, 'password': 'adminpass1'})
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_login_with_wrong_password_returns_401(self, api, admin_user):
        resp = api.post(self.URL, {'email': admin_user.email, 'password': 'wrongpass'})
        assert resp.status_code == 401

    def test_login_with_unknown_email_returns_401(self, api):
        resp = api.post(self.URL, {'email': 'nobody@example.com', 'password': 'pass'})
        assert resp.status_code == 401

    def test_login_email_is_case_insensitive(self, api, admin_user):
        resp = api.post(self.URL, {'email': admin_user.email.upper(), 'password': 'adminpass1'})
        assert resp.status_code == 200

    def test_username_field_no_longer_accepted(self, api, admin_user):
        resp = api.post(self.URL, {'username': admin_user.username, 'password': 'adminpass1'})
        assert resp.status_code == 400


# ── RegisterView ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegisterView:
    URL = '/api/v1/auth/register/'

    def test_creates_org_user_person(self, api):
        resp = api.post(self.URL, {
            'name': 'Jane Doe', 'email': 'jane@example.com',
            'password': 'securepass', 'plan': 'individual', 'org_name': 'Janes Co',
        })
        assert resp.status_code == 201
        assert Organisation.objects.filter(slug='janes-co').exists()
        assert User.objects.filter(email='jane@example.com').exists()
        assert Person.objects.filter(email='jane@example.com').exists()

    def test_returns_jwt_tokens(self, api):
        resp = api.post(self.URL, {
            'name': 'Tom', 'email': 'tom@example.com',
            'password': 'securepass', 'plan': 'team', 'org_name': 'Toms Inc',
        })
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_user_is_org_admin(self, api):
        api.post(self.URL, {
            'name': 'Alice', 'email': 'alice@example.com',
            'password': 'securepass', 'plan': 'individual', 'org_name': 'Alice Ltd',
        })
        user = User.objects.get(email='alice@example.com')
        assert user.is_org_admin is True

    def test_duplicate_email_rejected(self, api, admin_user):
        resp = api.post(self.URL, {
            'name': 'Dup', 'email': admin_user.email,
            'password': 'securepass', 'plan': 'individual', 'org_name': 'New Org',
        })
        assert resp.status_code == 400

    def test_duplicate_org_name_rejected(self, api, org):
        resp = api.post(self.URL, {
            'name': 'New User', 'email': 'newuser@example.com',
            'password': 'securepass', 'plan': 'individual', 'org_name': org.name,
        })
        assert resp.status_code == 400

    def test_short_password_rejected(self, api):
        resp = api.post(self.URL, {
            'name': 'Test', 'email': 'test@example.com',
            'password': 'short', 'plan': 'individual', 'org_name': 'Shortpass Co',
        })
        assert resp.status_code == 400

    def test_invalid_plan_rejected(self, api):
        resp = api.post(self.URL, {
            'name': 'Test', 'email': 'test@example.com',
            'password': 'securepass', 'plan': 'enterprise', 'org_name': 'Ent Co',
        })
        assert resp.status_code == 400

    def test_org_plan_stored(self, api):
        api.post(self.URL, {
            'name': 'Team Lead', 'email': 'lead@example.com',
            'password': 'securepass', 'plan': 'team', 'org_name': 'Team Org',
        })
        org = Organisation.objects.get(slug='team-org')
        assert org.plan == 'team'


# ── InviteView ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInviteView:
    URL = '/api/v1/auth/invite/'

    def test_admin_can_invite(self, admin_client):
        with patch('apps.accounts.views.send_mail') as mock_send:
            resp = admin_client.post(self.URL, {'email': 'newbie@acme.com'})
        assert resp.status_code == 201
        assert Invitation.objects.filter(email='newbie@acme.com').exists()
        mock_send.assert_called_once()

    def test_non_admin_cannot_invite(self, member_client):
        resp = member_client.post(self.URL, {'email': 'newbie@acme.com'})
        assert resp.status_code == 403

    def test_unauthenticated_cannot_invite(self, api):
        resp = api.post(self.URL, {'email': 'newbie@acme.com'})
        assert resp.status_code == 401

    def test_existing_member_rejected(self, admin_client, member_user):
        resp = admin_client.post(self.URL, {'email': member_user.email})
        assert resp.status_code == 400

    def test_reinvite_refreshes_token(self, admin_client, org):
        old_invite = Invitation.create_for(org, 'reinvite@acme.com', None)
        old_token = old_invite.token
        with patch('apps.accounts.views.send_mail'):
            admin_client.post(self.URL, {'email': 'reinvite@acme.com'})
        old_invite.refresh_from_db()
        assert old_invite.token != old_token


# ── ValidateInviteView ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestValidateInviteView:
    URL = '/api/v1/auth/invite/validate/'

    def test_valid_token_returns_email_and_org(self, api, org, admin_user):
        invite = Invitation.create_for(org, 'guest@acme.com', admin_user)
        resp = api.get(self.URL, {'token': invite.token})
        assert resp.status_code == 200
        assert resp.data['email'] == 'guest@acme.com'
        assert resp.data['org_name'] == org.name

    def test_unknown_token_returns_404(self, api):
        resp = api.get(self.URL, {'token': 'unknowntoken'})
        assert resp.status_code == 404

    def test_expired_token_returns_410(self, api, org, admin_user):
        from django.utils import timezone
        from datetime import timedelta
        invite = Invitation.create_for(org, 'expired@acme.com', admin_user)
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        resp = api.get(self.URL, {'token': invite.token})
        assert resp.status_code == 410

    def test_used_token_returns_410(self, api, org, admin_user):
        from django.utils import timezone
        invite = Invitation.create_for(org, 'used@acme.com', admin_user)
        invite.accepted_at = timezone.now()
        invite.save(update_fields=['accepted_at'])
        resp = api.get(self.URL, {'token': invite.token})
        assert resp.status_code == 410


# ── AcceptInviteView ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAcceptInviteView:
    URL = '/api/v1/auth/invite/accept/'

    @pytest.fixture
    def invite(self, org, admin_user):
        return Invitation.create_for(org, 'newmember@acme.com', admin_user)

    def test_accept_creates_user(self, api, invite):
        api.post(self.URL, {'token': invite.token, 'name': 'New Member', 'password': 'newpass12'})
        assert User.objects.filter(email='newmember@acme.com').exists()

    def test_accept_creates_person(self, api, invite):
        api.post(self.URL, {'token': invite.token, 'name': 'New Member', 'password': 'newpass12'})
        assert Person.objects.filter(email='newmember@acme.com').exists()

    def test_accept_marks_invite_used(self, api, invite):
        api.post(self.URL, {'token': invite.token, 'name': 'New Member', 'password': 'newpass12'})
        invite.refresh_from_db()
        assert invite.accepted_at is not None

    def test_accept_returns_jwt(self, api, invite):
        resp = api.post(self.URL, {'token': invite.token, 'name': 'New Member', 'password': 'newpass12'})
        assert resp.status_code == 201
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_accept_user_not_org_admin(self, api, invite):
        api.post(self.URL, {'token': invite.token, 'name': 'New Member', 'password': 'newpass12'})
        user = User.objects.get(email='newmember@acme.com')
        assert user.is_org_admin is False

    def test_invalid_token_rejected(self, api):
        resp = api.post(self.URL, {'token': 'badtoken', 'name': 'X', 'password': 'newpass12'})
        assert resp.status_code == 400

    def test_expired_token_rejected(self, api, org, admin_user):
        from django.utils import timezone
        from datetime import timedelta
        invite = Invitation.create_for(org, 'exp@acme.com', admin_user)
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        resp = api.post(self.URL, {'token': invite.token, 'name': 'X', 'password': 'newpass12'})
        assert resp.status_code == 400


# ── LinkSlack action ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLinkSlack:
    def _url(self, person_id):
        return f'/api/v1/persons/{person_id}/link-slack/'

    def test_user_can_link_own_slack(self, member_client, member_user):
        person = member_user.person
        resp = member_client.post(self._url(person.id), {'slack_user_id': 'U123ABC'})
        assert resp.status_code == 200
        person.refresh_from_db()
        assert person.slack_user_id == 'U123ABC'

    def test_admin_can_link_any_person(self, admin_client, member_user):
        person = member_user.person
        resp = admin_client.post(self._url(person.id), {'slack_user_id': 'U999ZZZ'})
        assert resp.status_code == 200
        person.refresh_from_db()
        assert person.slack_user_id == 'U999ZZZ'

    def test_member_cannot_link_other_person(self, member_client, admin_user):
        admin_person = admin_user.person
        resp = member_client.post(self._url(admin_person.id), {'slack_user_id': 'UHACK'})
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, api, member_user):
        person = member_user.person
        resp = api.post(self._url(person.id), {'slack_user_id': 'UXXX'})
        assert resp.status_code == 401

    def test_missing_slack_user_id_rejected(self, member_client, member_user):
        person = member_user.person
        resp = member_client.post(self._url(person.id), {})
        assert resp.status_code == 400
