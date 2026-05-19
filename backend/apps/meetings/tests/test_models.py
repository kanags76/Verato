"""Model tests for MeetingTopic and Week 3.5 Meeting fields."""
import pytest
from django.utils import timezone
from apps.accounts.models import Organisation
from apps.meetings.models import Meeting, MeetingTopic


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org,
        title='Q2 Planning',
        occurred_at=timezone.now(),
        processing_status=Meeting.ProcessingStatus.COMPLETE,
    )


@pytest.mark.django_db
class TestMeetingWeek35Fields:
    def test_meeting_type_defaults_to_other(self, meeting):
        assert meeting.meeting_type == Meeting.MeetingType.OTHER

    def test_meeting_summary_defaults_blank(self, meeting):
        assert meeting.summary == ''

    def test_meeting_type_choices_all_accepted(self, org):
        for choice in Meeting.MeetingType.values:
            m = Meeting.objects.create(
                organisation=org,
                title=f'Meeting {choice}',
                occurred_at=timezone.now(),
                meeting_type=choice,
            )
            assert m.meeting_type == choice

    def test_meeting_type_and_summary_save(self, meeting):
        meeting.meeting_type = Meeting.MeetingType.LEADERSHIP
        meeting.summary = 'Leadership review of Q2 priorities.'
        meeting.save(update_fields=['meeting_type', 'summary'])

        meeting.refresh_from_db()
        assert meeting.meeting_type == 'leadership'
        assert meeting.summary == 'Leadership review of Q2 priorities.'


@pytest.mark.django_db
class TestMeetingTopicModel:
    def test_create_topic(self, org, meeting):
        topic = MeetingTopic.objects.create(
            organisation=org,
            meeting=meeting,
            label='q2 board prep',
            confidence=0.95,
        )
        assert topic.label == 'q2 board prep'
        assert topic.confidence == 0.95
        assert topic.organisation == org

    def test_topic_accessible_via_meeting_related_name(self, org, meeting):
        MeetingTopic.objects.create(organisation=org, meeting=meeting, label='pricing', confidence=0.9)
        MeetingTopic.objects.create(organisation=org, meeting=meeting, label='hiring', confidence=0.85)
        assert meeting.topics.count() == 2

    def test_meeting_topics_deleted_with_meeting(self, org, meeting):
        MeetingTopic.objects.create(organisation=org, meeting=meeting, label='topic a', confidence=0.9)
        meeting_id = meeting.id
        meeting.delete()
        assert MeetingTopic.objects.filter(meeting_id=meeting_id).count() == 0

    def test_get_or_create_deduplication(self, org, meeting):
        MeetingTopic.objects.get_or_create(
            organisation=org, meeting=meeting, label='emea pricing',
            defaults={'confidence': 0.9},
        )
        MeetingTopic.objects.get_or_create(
            organisation=org, meeting=meeting, label='emea pricing',
            defaults={'confidence': 0.9},
        )
        assert MeetingTopic.objects.filter(meeting=meeting, label='emea pricing').count() == 1

    def test_same_label_different_meetings_creates_two_records(self, org):
        m1 = Meeting.objects.create(organisation=org, title='M1', occurred_at=timezone.now())
        m2 = Meeting.objects.create(organisation=org, title='M2', occurred_at=timezone.now())
        MeetingTopic.objects.create(organisation=org, meeting=m1, label='pricing', confidence=0.9)
        MeetingTopic.objects.create(organisation=org, meeting=m2, label='pricing', confidence=0.9)
        assert MeetingTopic.objects.filter(label='pricing').count() == 2
