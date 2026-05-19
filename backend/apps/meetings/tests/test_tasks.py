"""
Task tests for process_meeting and process_import (Week 3.5).

All tasks are called synchronously via .apply() — no Celery worker needed.
Gemini is mocked so no ADC token required.
"""
import pytest
from unittest.mock import patch
from django.utils import timezone

from apps.accounts.models import Organisation, Person
from apps.commitments.models import Commitment, CommitmentTag
from apps.meetings.models import Meeting, MeetingParticipant, MeetingTopic
from apps.meetings.tasks import process_meeting, process_import


# ── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def person(org):
    return Person.objects.create(organisation=org, name='Alice')


@pytest.fixture
def meeting(org, person):
    m = Meeting.objects.create(
        organisation=org,
        title='Q2 Planning',
        occurred_at=timezone.now(),
        raw_transcript='Alice will send the report by Friday.',
        word_count=8,
        processing_status=Meeting.ProcessingStatus.PENDING,
    )
    MeetingParticipant.objects.create(meeting=m, person=person)
    return m


@pytest.fixture
def import_meeting(org):
    return Meeting.objects.create(
        organisation=org,
        title='Prior Commitments Import',
        occurred_at=timezone.now(),
        platform=Meeting.Platform.IMPORT,
        raw_transcript='Alice - send report - May 2026',
        processing_status=Meeting.ProcessingStatus.PENDING,
    )


MOCK_EXTRACTION_RESULT = {
    "commitments": [
        {
            "raw_text": "Alice will send the report by Friday.",
            "normalised_text": "Alice will send the report by Friday 2026-05-01.",
            "commit_type": "explicit",
            "owner_name": "Alice",
            "deadline_text": "by Friday",
            "deadline_resolved": "2026-05-01",
            "confidence": 0.93,
            "tags": ["report delivery", "q2 planning"],
        }
    ],
    "topics": [
        {"label": "report delivery", "confidence": 0.95},
        {"label": "q2 planning",     "confidence": 0.88},
    ],
    "meeting_type": "team",
    "summary": "Team reviewed Q2 report delivery timeline.",
}

MOCK_IMPORT_RESULT = {
    "commitments": [
        {
            "raw_text": "Alice - send report - May 2026",
            "normalised_text": "Alice to send the report by May 2026.",
            "commit_type": "explicit",
            "owner_name": "Alice",
            "deadline_text": "May 2026",
            "deadline_resolved": "2026-05-31",
            "confidence": 0.88,
            "tags": ["report delivery"],
            "source": "import",
        }
    ],
    "topics": [],
    "meeting_type": "other",
    "summary": "",
}


# ── process_meeting tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProcessMeetingNonRegression:
    """Verify all Week 1–3 behaviour is preserved."""

    def test_commitments_still_created_pending_review(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        assert Commitment.objects.filter(meeting=meeting).count() == 1
        assert Commitment.objects.get(meeting=meeting).status == Commitment.Status.PENDING_REVIEW

    def test_meeting_status_set_to_complete(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.processing_status == Meeting.ProcessingStatus.COMPLETE

    def test_processed_at_set(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.processed_at is not None

    def test_owner_resolved_to_person(self, org, meeting, person):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        commitment = Commitment.objects.get(meeting=meeting)
        assert commitment.owner == person

    def test_source_set_to_transcript(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        commitment = Commitment.objects.get(meeting=meeting)
        assert commitment.source == Commitment.Source.TRANSCRIPT


@pytest.mark.django_db
class TestProcessMeetingGraphWrites:
    """Verify Week 3.5 graph data is written correctly."""

    def test_meeting_type_saved(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.meeting_type == 'team'

    def test_meeting_summary_saved(self, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.summary == 'Team reviewed Q2 report delivery timeline.'

    def test_meeting_topics_created(self, org, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        assert MeetingTopic.objects.filter(meeting=meeting).count() == 2
        labels = set(MeetingTopic.objects.filter(meeting=meeting).values_list('label', flat=True))
        assert labels == {'report delivery', 'q2 planning'}

    def test_commitment_tags_linked(self, org, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        commitment = Commitment.objects.get(meeting=meeting)
        labels = set(commitment.tags.values_list('label', flat=True))
        assert labels == {'report delivery', 'q2 planning'}

    def test_commitment_tag_records_created(self, org, meeting):
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        assert CommitmentTag.objects.filter(organisation=org).count() == 2

    def test_tag_deduplication_across_two_meetings(self, org, person):
        m1 = Meeting.objects.create(
            organisation=org, title='M1', occurred_at=timezone.now(),
            raw_transcript='t', processing_status=Meeting.ProcessingStatus.PENDING,
        )
        m2 = Meeting.objects.create(
            organisation=org, title='M2', occurred_at=timezone.now(),
            raw_transcript='t', processing_status=Meeting.ProcessingStatus.PENDING,
        )
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(m1.id)], throw=True)
            process_meeting.apply(args=[str(m2.id)], throw=True)
        # Same tag labels → one CommitmentTag record per label (deduped per org)
        assert CommitmentTag.objects.filter(organisation=org, label='report delivery').count() == 1

    def test_person_meeting_count_incremented(self, meeting, person):
        assert person.meeting_count == 0
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        person.refresh_from_db()
        assert person.meeting_count == 1

    def test_person_first_seen_at_set(self, meeting, person):
        assert person.first_seen_at is None
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        person.refresh_from_db()
        assert person.first_seen_at is not None

    def test_person_first_seen_at_not_overwritten_on_second_meeting(self, org, person):
        m1 = Meeting.objects.create(
            organisation=org, title='M1', occurred_at=timezone.now(),
            raw_transcript='t', processing_status=Meeting.ProcessingStatus.PENDING,
        )
        MeetingParticipant.objects.create(meeting=m1, person=person)
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(m1.id)], throw=True)
        person.refresh_from_db()
        first_time = person.first_seen_at

        m2 = Meeting.objects.create(
            organisation=org, title='M2', occurred_at=timezone.now(),
            raw_transcript='t', processing_status=Meeting.ProcessingStatus.PENDING,
        )
        MeetingParticipant.objects.create(meeting=m2, person=person)
        with patch('apps.meetings.tasks.extract_commitments', return_value=MOCK_EXTRACTION_RESULT):
            process_meeting.apply(args=[str(m2.id)], throw=True)
        person.refresh_from_db()
        assert person.first_seen_at == first_time  # unchanged
        assert person.meeting_count == 2


@pytest.mark.django_db
class TestProcessMeetingFallbacks:
    """Missing graph metadata should not fail the pipeline."""

    def test_missing_topics_does_not_fail(self, meeting):
        result_no_topics = {**MOCK_EXTRACTION_RESULT, "topics": []}
        with patch('apps.meetings.tasks.extract_commitments', return_value=result_no_topics):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.processing_status == Meeting.ProcessingStatus.COMPLETE
        assert MeetingTopic.objects.filter(meeting=meeting).count() == 0

    def test_empty_commitments_still_completes(self, meeting):
        empty_result = {"commitments": [], "topics": [], "meeting_type": "other", "summary": ""}
        with patch('apps.meetings.tasks.extract_commitments', return_value=empty_result):
            process_meeting.apply(args=[str(meeting.id)], throw=True)
        meeting.refresh_from_db()
        assert meeting.processing_status == Meeting.ProcessingStatus.COMPLETE
        assert Commitment.objects.filter(meeting=meeting).count() == 0


# ── process_import tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProcessImportNonRegression:
    def test_commitments_created_pending_review(self, import_meeting):
        with patch('apps.meetings.tasks.extract_from_document', return_value=MOCK_IMPORT_RESULT):
            process_import.apply(args=[str(import_meeting.id)], throw=True)
        assert Commitment.objects.filter(meeting=import_meeting).count() == 1
        assert Commitment.objects.get(meeting=import_meeting).status == Commitment.Status.PENDING_REVIEW

    def test_source_set_to_import(self, import_meeting):
        with patch('apps.meetings.tasks.extract_from_document', return_value=MOCK_IMPORT_RESULT):
            process_import.apply(args=[str(import_meeting.id)], throw=True)
        commitment = Commitment.objects.get(meeting=import_meeting)
        assert commitment.source == Commitment.Source.IMPORT

    def test_meeting_status_set_to_complete(self, import_meeting):
        with patch('apps.meetings.tasks.extract_from_document', return_value=MOCK_IMPORT_RESULT):
            process_import.apply(args=[str(import_meeting.id)], throw=True)
        import_meeting.refresh_from_db()
        assert import_meeting.processing_status == Meeting.ProcessingStatus.COMPLETE


@pytest.mark.django_db
class TestProcessImportGraphWrites:
    def test_import_commitments_have_tags(self, import_meeting):
        with patch('apps.meetings.tasks.extract_from_document', return_value=MOCK_IMPORT_RESULT):
            process_import.apply(args=[str(import_meeting.id)], throw=True)
        commitment = Commitment.objects.get(meeting=import_meeting)
        assert 'report delivery' in commitment.tags.values_list('label', flat=True)

    def test_import_has_no_meeting_topics(self, import_meeting):
        with patch('apps.meetings.tasks.extract_from_document', return_value=MOCK_IMPORT_RESULT):
            process_import.apply(args=[str(import_meeting.id)], throw=True)
        assert MeetingTopic.objects.filter(meeting=import_meeting).count() == 0
