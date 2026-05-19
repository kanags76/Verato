"""API tests for extended Person endpoints (Week 3.5)."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User, Person
from apps.commitments.models import Commitment, CommitmentTag
from apps.meetings.models import Meeting, MeetingParticipant, MeetingTopic


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
def person(org):
    return Person.objects.create(
        organisation=org, name='Alice',
        first_seen_at=timezone.now(), meeting_count=3,
    )


@pytest.fixture
def meeting_with_data(org, person):
    m = Meeting.objects.create(
        organisation=org, title='Q2 Planning',
        occurred_at=timezone.now(),
        meeting_type=Meeting.MeetingType.LEADERSHIP,
        summary='Q2 planning discussion.',
        processing_status=Meeting.ProcessingStatus.COMPLETE,
    )
    MeetingParticipant.objects.create(meeting=m, person=person)
    MeetingTopic.objects.create(organisation=org, meeting=m, label='q2 planning', confidence=0.95)

    tag = CommitmentTag.objects.create(organisation=org, label='q2 planning')
    c = Commitment.objects.create(
        organisation=org, meeting=m,
        raw_text='Alice will send report.',
        normalised_text='Alice will send report.',
        confidence=0.9, owner=person,
    )
    c.tags.add(tag)
    return m


@pytest.mark.django_db
class TestPersonDetailExtended:
    def test_person_detail_includes_meeting_count(self, client, person):
        resp = client.get(f'/api/v1/persons/{person.id}/')
        assert resp.status_code == 200
        assert resp.data['meeting_count'] == 3

    def test_person_detail_includes_first_seen_at(self, client, person):
        resp = client.get(f'/api/v1/persons/{person.id}/')
        assert 'first_seen_at' in resp.data
        assert resp.data['first_seen_at'] is not None

    def test_person_detail_includes_recent_topics(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/')
        assert 'recent_topics' in resp.data
        assert 'q2 planning' in resp.data['recent_topics']

    def test_person_detail_recent_topics_empty_for_new_person(self, client, org):
        p = Person.objects.create(organisation=org, name='Bob')
        u = User.objects.create_user(username='bob', password='pass', organisation=org)
        c = APIClient()
        c.force_authenticate(user=u)
        resp = c.get(f'/api/v1/persons/{p.id}/')
        assert resp.data['recent_topics'] == []

    def test_person_list_still_works(self, client, person):
        resp = client.get('/api/v1/persons/')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestPersonTimeline:
    def test_timeline_returns_200(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        assert resp.status_code == 200

    def test_timeline_has_person_and_timeline_keys(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        assert 'person' in resp.data
        assert 'timeline' in resp.data

    def test_timeline_chronological_order(self, client, org, person):
        earlier = timezone.now().replace(year=2026, month=1, day=1)
        later   = timezone.now().replace(year=2026, month=6, day=1)
        m1 = Meeting.objects.create(
            organisation=org, title='M1', occurred_at=later,
            processing_status=Meeting.ProcessingStatus.COMPLETE,
        )
        m2 = Meeting.objects.create(
            organisation=org, title='M2', occurred_at=earlier,
            processing_status=Meeting.ProcessingStatus.COMPLETE,
        )
        MeetingParticipant.objects.create(meeting=m1, person=person)
        MeetingParticipant.objects.create(meeting=m2, person=person)

        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        titles = [e['meeting']['title'] for e in resp.data['timeline']]
        assert titles.index('M2') < titles.index('M1')

    def test_timeline_includes_commitment_for_person(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        assert len(resp.data['timeline']) == 1
        entry = resp.data['timeline'][0]
        assert len(entry['commitments']) == 1
        assert entry['commitments'][0]['normalised_text'] == 'Alice will send report.'

    def test_timeline_commitment_includes_tags(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        entry = resp.data['timeline'][0]
        tags = entry['commitments'][0]['tags']
        assert 'q2 planning' in tags

    def test_timeline_includes_meeting_topics(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        entry = resp.data['timeline'][0]
        topic_labels = [t['label'] for t in entry['topics']]
        assert 'q2 planning' in topic_labels

    def test_timeline_only_complete_meetings(self, client, org, person):
        pending = Meeting.objects.create(
            organisation=org, title='Pending', occurred_at=timezone.now(),
            processing_status=Meeting.ProcessingStatus.PENDING,
        )
        MeetingParticipant.objects.create(meeting=pending, person=person)
        resp = client.get(f'/api/v1/persons/{person.id}/timeline/')
        titles = [e['meeting']['title'] for e in resp.data['timeline']]
        assert 'Pending' not in titles

    def test_timeline_unauthenticated_returns_401(self, person):
        resp = APIClient().get(f'/api/v1/persons/{person.id}/timeline/')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPersonTopics:
    def test_topics_returns_200(self, client, person):
        resp = client.get(f'/api/v1/persons/{person.id}/topics/')
        assert resp.status_code == 200

    def test_topics_returns_label_and_count(self, client, person, meeting_with_data):
        resp = client.get(f'/api/v1/persons/{person.id}/topics/')
        assert len(resp.data) >= 1
        assert 'label' in resp.data[0]
        assert 'count' in resp.data[0]
        assert 'last_seen' in resp.data[0]

    def test_topics_empty_for_person_with_no_commitments(self, client, org):
        p = Person.objects.create(organisation=org, name='New Person')
        u = User.objects.create_user(username='newperson', password='pass', organisation=org)
        c = APIClient()
        c.force_authenticate(user=u)
        resp = c.get(f'/api/v1/persons/{p.id}/topics/')
        assert resp.data == []
