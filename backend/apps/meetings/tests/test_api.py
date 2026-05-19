"""API tests for extended Meeting endpoints (Week 3.5)."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User
from apps.meetings.models import Meeting, MeetingTopic


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def user(org):
    u = User.objects.create_user(username='cos', password='pass', organisation=org)
    return u


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org,
        title='Leadership Sync',
        occurred_at=timezone.now(),
        meeting_type=Meeting.MeetingType.LEADERSHIP,
        summary='Team reviewed Q2 priorities.',
        processing_status=Meeting.ProcessingStatus.COMPLETE,
    )


@pytest.fixture
def topics(org, meeting):
    MeetingTopic.objects.create(organisation=org, meeting=meeting, label='q2 planning', confidence=0.95)
    MeetingTopic.objects.create(organisation=org, meeting=meeting, label='hiring', confidence=0.88)
    return meeting.topics.all()


@pytest.mark.django_db
class TestMeetingDetailExtended:
    def test_meeting_detail_includes_meeting_type(self, client, meeting):
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.status_code == 200
        assert resp.data['meeting_type'] == 'leadership'

    def test_meeting_detail_includes_summary(self, client, meeting):
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.data['summary'] == 'Team reviewed Q2 priorities.'

    def test_meeting_detail_includes_topics(self, client, meeting, topics):
        resp = client.get(f'/api/v1/meetings/{meeting.id}/')
        assert 'topics' in resp.data
        topic_labels = [t['label'] for t in resp.data['topics']]
        assert 'q2 planning' in topic_labels
        assert 'hiring' in topic_labels

    def test_meeting_detail_topics_empty_for_import(self, client, org):
        m = Meeting.objects.create(
            organisation=org, title='Import', occurred_at=timezone.now(),
            platform=Meeting.Platform.IMPORT, processing_status=Meeting.ProcessingStatus.COMPLETE,
        )
        resp = client.get(f'/api/v1/meetings/{m.id}/')
        assert resp.data['topics'] == []

    def test_meeting_list_still_works(self, client, meeting):
        resp = client.get('/api/v1/meetings/')
        assert resp.status_code == 200
        assert len(resp.data['results']) >= 1

    def test_meeting_list_includes_meeting_type(self, client, meeting):
        resp = client.get('/api/v1/meetings/')
        first = resp.data['results'][0]
        assert 'meeting_type' in first
        assert 'summary' in first
        assert 'topics' in first

    def test_unauthenticated_returns_401(self, meeting):
        resp = APIClient().get(f'/api/v1/meetings/{meeting.id}/')
        assert resp.status_code == 401
