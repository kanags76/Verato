"""Tests for bulk-confirm, nudge, tag autocomplete, and tags writable (PATCH)."""
import pytest
from unittest.mock import MagicMock, patch
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, Person, User
from apps.commitments.models import Commitment, CommitmentTag, ExtractionFeedback
from apps.meetings.models import Meeting


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


@pytest.fixture
def pending(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Alice will send the report.',
        normalised_text='Alice will send the report.',
        confidence=0.9,
        status=Commitment.Status.PENDING_REVIEW,
    )


@pytest.fixture
def low_confidence_pending(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Maybe Bob will look into it.',
        normalised_text='Maybe Bob will look into it.',
        confidence=0.3,
        status=Commitment.Status.PENDING_REVIEW,
    )


@pytest.fixture
def owner(org):
    u = User.objects.create_user(username='owner', password='pass', organisation=org)
    p = Person.objects.create(organisation=org, user=u, name='Owner Person', email='owner@test.com')
    return p


# ── Bulk confirm ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBulkConfirm:
    URL = '/api/v1/commitments/bulk-confirm/'

    def test_confirms_all_pending(self, client, pending, low_confidence_pending):
        resp = client.post(self.URL, format='json')
        assert resp.status_code == 200
        assert resp.data['confirmed'] == 2
        pending.refresh_from_db()
        assert pending.status == Commitment.Status.ACTIVE

    def test_min_confidence_filter(self, client, pending, low_confidence_pending):
        resp = client.post(self.URL, {'min_confidence': 0.8}, format='json')
        assert resp.status_code == 200
        assert resp.data['confirmed'] == 1
        pending.refresh_from_db()
        assert pending.status == Commitment.Status.ACTIVE
        low_confidence_pending.refresh_from_db()
        assert low_confidence_pending.status == Commitment.Status.PENDING_REVIEW

    def test_creates_feedback_records(self, client, pending):
        client.post(self.URL, format='json')
        assert ExtractionFeedback.objects.filter(
            commitment=pending,
            feedback_type=ExtractionFeedback.FeedbackType.CONFIRMED,
        ).exists()

    def test_does_not_affect_active_commitments(self, client, org, meeting):
        active = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='Active one.', normalised_text='Active one.',
            confidence=0.9, status=Commitment.Status.ACTIVE,
        )
        resp = client.post(self.URL, format='json')
        assert resp.data['confirmed'] == 0
        active.refresh_from_db()
        assert active.status == Commitment.Status.ACTIVE

    def test_meeting_filter_scopes_to_one_meeting(self, client, org, meeting):
        other_meeting = Meeting.objects.create(
            organisation=org, title='Other Meeting', occurred_at=timezone.now(),
        )
        other_pending = Commitment.objects.create(
            organisation=org, meeting=other_meeting,
            raw_text='Other commitment.', normalised_text='Other commitment.',
            confidence=0.9, status=Commitment.Status.PENDING_REVIEW,
        )
        resp = client.post(self.URL, {'meeting': str(meeting.id)}, format='json')
        assert resp.status_code == 200
        # only the commitments in `meeting` are confirmed (pending + low_confidence_pending
        # are both in the `meeting` fixture — but none may exist here; just verify other_pending untouched)
        other_pending.refresh_from_db()
        assert other_pending.status == Commitment.Status.PENDING_REVIEW

    def test_meeting_filter_with_min_confidence(self, client, org, meeting, pending, low_confidence_pending):
        resp = client.post(
            self.URL,
            {'meeting': str(meeting.id), 'min_confidence': 0.8},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['confirmed'] == 1  # only high-confidence one
        low_confidence_pending.refresh_from_db()
        assert low_confidence_pending.status == Commitment.Status.PENDING_REVIEW

    def test_invalid_min_confidence_returns_400(self, client):
        resp = client.post(self.URL, {'min_confidence': 'not-a-float'}, format='json')
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self):
        resp = APIClient().post('/api/v1/commitments/bulk-confirm/', format='json')
        assert resp.status_code == 401


# ── Nudge ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNudge:
    def _url(self, commitment_id):
        return f'/api/v1/commitments/{commitment_id}/nudge/'

    def test_no_owner_returns_400(self, client, pending):
        resp = client.post(self._url(pending.id))
        assert resp.status_code == 400
        assert 'no owner' in resp.data['detail']

    def test_owner_without_slack_returns_400(self, client, pending, owner):
        pending.owner = owner
        pending.save(update_fields=['owner'])
        resp = client.post(self._url(pending.id))
        assert resp.status_code == 400
        assert 'Slack user ID' in resp.data['detail']

    def test_slack_not_configured_returns_502(self, client, pending, owner):
        owner.slack_user_id = 'U123'
        owner.save(update_fields=['slack_user_id'])
        pending.owner = owner
        pending.save(update_fields=['owner'])

        with patch('apps.notifications.slack._get_client', return_value=None):
            resp = client.post(self._url(pending.id))

        assert resp.status_code == 502

    def test_sends_nudge_and_returns_channel(self, client, pending, owner):
        owner.slack_user_id = 'U123ABC'
        owner.save(update_fields=['slack_user_id'])
        pending.owner = owner
        pending.save(update_fields=['owner'])

        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {'channel': 'D999'}
        with patch('apps.notifications.slack._get_client', return_value=mock_client):
            resp = client.post(self._url(pending.id))

        assert resp.status_code == 200
        assert resp.data['detail'] == 'Nudge sent.'
        assert resp.data['channel'] == 'D999'


# ── Tag autocomplete ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTagList:
    URL = '/api/v1/tags/'

    def test_unauthenticated_returns_401(self):
        resp = APIClient().get(self.URL)
        assert resp.status_code == 401

    def test_returns_org_tags(self, client, org):
        CommitmentTag.objects.create(organisation=org, label='budget')
        CommitmentTag.objects.create(organisation=org, label='hiring')
        resp = client.get(self.URL)
        assert resp.status_code == 200
        labels = [t['label'] for t in resp.data]
        assert 'budget' in labels
        assert 'hiring' in labels

    def test_prefix_filter(self, client, org):
        CommitmentTag.objects.create(organisation=org, label='budget')
        CommitmentTag.objects.create(organisation=org, label='hiring')
        resp = client.get(self.URL, {'q': 'bu'})
        assert resp.status_code == 200
        labels = [t['label'] for t in resp.data]
        assert 'budget' in labels
        assert 'hiring' not in labels

    def test_prefix_filter_case_insensitive(self, client, org):
        CommitmentTag.objects.create(organisation=org, label='Budget')
        resp = client.get(self.URL, {'q': 'bud'})
        labels = [t['label'] for t in resp.data]
        assert 'Budget' in labels

    def test_other_org_tags_not_returned(self, client, org):
        other_org = Organisation.objects.create(name='Other', slug='other')
        CommitmentTag.objects.create(organisation=other_org, label='secret-tag')
        resp = client.get(self.URL)
        labels = [t['label'] for t in resp.data]
        assert 'secret-tag' not in labels

    def test_returns_usage_count(self, client, org, meeting):
        tag = CommitmentTag.objects.create(organisation=org, label='roadmap')
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
        )
        c.tags.add(tag)
        resp = client.get(self.URL)
        roadmap = next(t for t in resp.data if t['label'] == 'roadmap')
        assert roadmap['usage'] == 1


# ── Tags writable on PATCH ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTagsWritable:
    def test_patch_sets_tags(self, client, org, meeting):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
        )
        resp = client.patch(f'/api/v1/commitments/{c.id}/', {'tags': ['hiring', 'budget']}, format='json')
        assert resp.status_code == 200
        assert set(resp.data['tags']) == {'hiring', 'budget'}

    def test_patch_tags_creates_get_or_creates(self, client, org, meeting):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
        )
        client.patch(f'/api/v1/commitments/{c.id}/', {'tags': ['roadmap']}, format='json')
        client.patch(f'/api/v1/commitments/{c.id}/', {'tags': ['roadmap']}, format='json')
        assert CommitmentTag.objects.filter(organisation=org, label='roadmap').count() == 1

    def test_patch_empty_tags_clears_them(self, client, org, meeting):
        tag = CommitmentTag.objects.create(organisation=org, label='budget')
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
        )
        c.tags.add(tag)
        resp = client.patch(f'/api/v1/commitments/{c.id}/', {'tags': []}, format='json')
        assert resp.status_code == 200
        assert resp.data['tags'] == []

    def test_tags_normalised_to_lowercase(self, client, org, meeting):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
        )
        resp = client.patch(f'/api/v1/commitments/{c.id}/', {'tags': ['BUDGET', '  Hiring  ']}, format='json')
        assert 'budget' in resp.data['tags']
        assert 'hiring' in resp.data['tags']
