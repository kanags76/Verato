import logging
from datetime import date

from celery import shared_task
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import Person
from apps.commitments.models import Commitment, CommitmentTag
from apps.meetings.models import Meeting, MeetingTopic, MeetingParticipant
from extraction.extractor import extract_commitments
from extraction.importer import extract_from_document

logger = logging.getLogger(__name__)


def _resolve_person(org, name: str):
    """
    Find or create a Person by name within the org.
    Tries exact match first, then first-name prefix match, then creates new.
    """
    if not name or not name.strip():
        return None
    name = name.strip()

    person = Person.objects.filter(organisation=org, name__iexact=name).first()
    if person:
        return person

    first_name = name.split()[0]
    person = Person.objects.filter(organisation=org, name__istartswith=first_name).first()
    if person:
        return person

    person, _ = Person.objects.get_or_create(organisation=org, name=name)
    return person


def _parse_deadline(date_str):
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _save_tags(commitment, org, tag_labels: list[str]):
    """Get-or-create CommitmentTag records and link to commitment."""
    for label in tag_labels:
        label = label.strip().lower()
        if not label:
            continue
        tag, _ = CommitmentTag.objects.get_or_create(organisation=org, label=label)
        commitment.tags.add(tag)


def _save_topics(meeting, org, topics: list[dict]):
    """Create MeetingTopic records for a processed meeting."""
    for topic in topics:
        label = topic.get("label", "").strip().lower()
        if not label:
            continue
        MeetingTopic.objects.get_or_create(
            organisation=org,
            meeting=meeting,
            label=label,
            defaults={"confidence": topic.get("confidence", 1.0)},
        )


def _update_person_lineage(person, meeting_occurred_at):
    """Increment meeting_count and set first_seen_at if not already set."""
    Person.objects.filter(pk=person.pk).update(meeting_count=F('meeting_count') + 1)
    if not person.first_seen_at:
        Person.objects.filter(pk=person.pk).update(first_seen_at=meeting_occurred_at)


@shared_task(bind=True, max_retries=2)
def process_meeting(self, meeting_id: str):
    """Extract commitments + graph metadata from a transcript. Save all as PENDING_REVIEW."""
    try:
        meeting = Meeting.objects.select_related('organisation').get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error("process_meeting: meeting %s not found", meeting_id)
        return

    meeting.processing_status = Meeting.ProcessingStatus.PROCESSING
    meeting.save(update_fields=['processing_status'])

    try:
        participants = list(meeting.participants.values_list('name', flat=True))
        result = extract_commitments(
            meeting.raw_transcript,
            participants,
            meeting_title=meeting.title,
            meeting_date=meeting.occurred_at.date().isoformat(),
        )

        org = meeting.organisation
        created = 0
        for item in result["commitments"]:
            owner = _resolve_person(org, item.get('owner_name', ''))
            commitment = Commitment.objects.create(
                organisation=org,
                meeting=meeting,
                raw_text=item['raw_text'],
                normalised_text=item['normalised_text'],
                commit_type=item.get('commit_type', Commitment.CommitType.EXPLICIT),
                confidence=item['confidence'],
                owner=owner,
                deadline=_parse_deadline(item.get('deadline_resolved')),
                source=Commitment.Source.TRANSCRIPT,
                status=Commitment.Status.PENDING_REVIEW,
            )
            _save_tags(commitment, org, item.get('tags', []))
            created += 1

        # Persist graph metadata
        _save_topics(meeting, org, result["topics"])

        # Store Gemini-detected participants as unconfirmed MeetingParticipant rows
        for speaker_name in result.get("participants", []):
            person = _resolve_person(org, speaker_name)
            if person:
                MeetingParticipant.objects.get_or_create(
                    meeting=meeting,
                    person=person,
                    defaults={
                        'speaker_label': speaker_name,
                        'confirmed': False,
                    },
                )

        meeting.meeting_type = result["meeting_type"]
        meeting.summary = result["summary"]
        meeting.processing_status = Meeting.ProcessingStatus.COMPLETE
        meeting.processed_at = timezone.now()
        meeting.save(update_fields=[
            'processing_status', 'processed_at', 'meeting_type', 'summary',
        ])

        # Update person lineage for all participants
        for participant in meeting.participants.all():
            _update_person_lineage(participant, meeting.occurred_at)

        logger.info(
            "process_meeting: %s → %d commitments, %d topics, type=%s",
            meeting_id, created, len(result["topics"]), result["meeting_type"],
        )

    except Exception as exc:
        logger.error("process_meeting: failed for %s: %s", meeting_id, exc)
        meeting.processing_status = Meeting.ProcessingStatus.FAILED
        meeting.processing_error = str(exc)[:2000]
        meeting.save(update_fields=['processing_status', 'processing_error'])
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=2)
def process_import(self, meeting_id: str):
    """Extract commitments from a prior-commitments document. Save as PENDING_REVIEW + source=import."""
    try:
        meeting = Meeting.objects.select_related('organisation').get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error("process_import: meeting %s not found", meeting_id)
        return

    meeting.processing_status = Meeting.ProcessingStatus.PROCESSING
    meeting.save(update_fields=['processing_status'])

    try:
        result = extract_from_document(meeting.raw_transcript)

        org = meeting.organisation
        created = 0
        for item in result["commitments"]:
            owner = _resolve_person(org, item.get('owner_name', ''))
            commitment = Commitment.objects.create(
                organisation=org,
                meeting=meeting,
                raw_text=item['raw_text'],
                normalised_text=item['normalised_text'],
                commit_type=item.get('commit_type', Commitment.CommitType.EXPLICIT),
                confidence=item['confidence'],
                owner=owner,
                deadline=_parse_deadline(item.get('deadline_resolved')),
                source=Commitment.Source.IMPORT,
                status=Commitment.Status.PENDING_REVIEW,
            )
            _save_tags(commitment, org, item.get('tags', []))
            created += 1

        # Import meetings have no topics or summary
        meeting.processing_status = Meeting.ProcessingStatus.COMPLETE
        meeting.processed_at = timezone.now()
        meeting.save(update_fields=['processing_status', 'processed_at'])
        logger.info("process_import: %s → %d commitments created", meeting_id, created)

    except Exception as exc:
        logger.error("process_import: failed for %s: %s", meeting_id, exc)
        meeting.processing_status = Meeting.ProcessingStatus.FAILED
        meeting.processing_error = str(exc)[:2000]
        meeting.save(update_fields=['processing_status', 'processing_error'])
        raise self.retry(exc=exc, countdown=30)
