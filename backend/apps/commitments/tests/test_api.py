"""API tests for Commitment tag filter (Week 3.5)."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User, Person
from apps.commitments.models import Commitment, CommitmentTag
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


@pytest.fixture
def two_commitments_one_tagged(org, meeting):
    tag = CommitmentTag.objects.create(organisation=org, label='q2 board prep')

    c1 = Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Commitment A', normalised_text='Commitment A', confidence=0.9,
    )
    c1.tags.add(tag)

    c2 = Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Commitment B', normalised_text='Commitment B', confidence=0.9,
    )
    return c1, c2, tag


@pytest.mark.django_db
class TestCommitmentTagFilter:
    def test_tag_filter_returns_matching(self, client, two_commitments_one_tagged):
        c1, c2, tag = two_commitments_one_tagged
        resp = client.get('/api/v1/commitments/', {'tags__label': 'q2 board prep'})
        assert resp.status_code == 200
        ids = [r['id'] for r in resp.data['results']]
        assert str(c1.id) in ids
        assert str(c2.id) not in ids

    def test_tag_filter_no_match_returns_empty(self, client, two_commitments_one_tagged):
        resp = client.get('/api/v1/commitments/', {'tags__label': 'nonexistent'})
        assert resp.status_code == 200
        assert len(resp.data['results']) == 0

    def test_commitment_list_still_works_no_filter(self, client, two_commitments_one_tagged):
        resp = client.get('/api/v1/commitments/')
        assert resp.status_code == 200
        assert len(resp.data['results']) == 2

    def test_existing_status_filter_still_works(self, client, two_commitments_one_tagged):
        resp = client.get('/api/v1/commitments/', {'status': 'pending_review'})
        assert resp.status_code == 200
        assert len(resp.data['results']) == 2

    def test_commitment_detail_includes_tags(self, client, two_commitments_one_tagged):
        c1, _, tag = two_commitments_one_tagged
        resp = client.get(f'/api/v1/commitments/{c1.id}/')
        assert resp.status_code == 200
        assert 'tags' in resp.data
        assert 'q2 board prep' in resp.data['tags']

    def test_commitment_detail_no_tags_returns_empty_list(self, client, two_commitments_one_tagged):
        _, c2, _ = two_commitments_one_tagged
        resp = client.get(f'/api/v1/commitments/{c2.id}/')
        assert resp.data['tags'] == []
