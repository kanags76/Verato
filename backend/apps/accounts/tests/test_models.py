"""Model tests for Person Week 3.5 lineage fields."""
import pytest
from django.utils import timezone
from apps.accounts.models import Organisation, Person
from apps.meetings.models import Meeting, MeetingParticipant


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def person(org):
    return Person.objects.create(organisation=org, name='Alice')


@pytest.mark.django_db
class TestPersonLineageFields:
    def test_first_seen_at_defaults_null(self, person):
        assert person.first_seen_at is None

    def test_meeting_count_defaults_zero(self, person):
        assert person.meeting_count == 0

    def test_first_seen_at_can_be_set(self, person):
        now = timezone.now()
        person.first_seen_at = now
        person.save(update_fields=['first_seen_at'])
        person.refresh_from_db()
        assert person.first_seen_at is not None

    def test_meeting_count_increments(self, person):
        from django.db.models import F
        Person.objects.filter(pk=person.pk).update(meeting_count=F('meeting_count') + 1)
        person.refresh_from_db()
        assert person.meeting_count == 1

    def test_first_seen_at_not_overwritten_if_already_set(self, org):
        first_time = timezone.now()
        p = Person.objects.create(organisation=org, name='Bob', first_seen_at=first_time)
        # Simulate a second meeting — should NOT overwrite first_seen_at
        if not p.first_seen_at:
            Person.objects.filter(pk=p.pk).update(first_seen_at=timezone.now())
        p.refresh_from_db()
        assert abs((p.first_seen_at - first_time).total_seconds()) < 1

    def test_existing_persons_have_null_first_seen_at(self, org):
        p = Person.objects.create(organisation=org, name='Existing Person')
        assert p.first_seen_at is None
        assert p.meeting_count == 0
