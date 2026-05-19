"""Tests for GET /api/v1/auth/invitations/."""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.accounts.models import Invitation, Organisation, Person, User

URL = '/api/v1/auth/invitations/'


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


@pytest.mark.django_db
class TestInvitationList:
    def test_admin_can_list_invitations(self, admin_client, org, admin_user):
        Invitation.create_for(org, 'alice@acme.com', admin_user)
        Invitation.create_for(org, 'bob@acme.com', admin_user)
        resp = admin_client.get(URL)
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_member_cannot_list_invitations(self, member_client):
        resp = member_client.get(URL)
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(URL)
        assert resp.status_code == 401

    def test_pending_status_on_valid_invite(self, admin_client, org, admin_user):
        Invitation.create_for(org, 'pending@acme.com', admin_user)
        resp = admin_client.get(URL)
        assert resp.data[0]['status'] == 'pending'
        assert resp.data[0]['email'] == 'pending@acme.com'

    def test_accepted_status_on_used_invite(self, admin_client, org, admin_user):
        invite = Invitation.create_for(org, 'used@acme.com', admin_user)
        invite.accepted_at = timezone.now()
        invite.save(update_fields=['accepted_at'])
        resp = admin_client.get(URL)
        assert resp.data[0]['status'] == 'accepted'

    def test_expired_status_on_old_invite(self, admin_client, org, admin_user):
        invite = Invitation.create_for(org, 'expired@acme.com', admin_user)
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        resp = admin_client.get(URL)
        assert resp.data[0]['status'] == 'expired'

    def test_other_org_invites_not_returned(self, admin_client, admin_user):
        other_org = Organisation.objects.create(name='Other', slug='other')
        Invitation.create_for(other_org, 'secret@other.com', admin_user)
        resp = admin_client.get(URL)
        assert resp.status_code == 200
        emails = [i['email'] for i in resp.data]
        assert 'secret@other.com' not in emails

    def test_returns_required_fields(self, admin_client, org, admin_user):
        Invitation.create_for(org, 'check@acme.com', admin_user)
        resp = admin_client.get(URL)
        item = resp.data[0]
        for field in ('id', 'email', 'status', 'expires_at', 'created_at'):
            assert field in item

    def test_empty_org_returns_empty_list(self, admin_client):
        resp = admin_client.get(URL)
        assert resp.status_code == 200
        assert resp.data == []
