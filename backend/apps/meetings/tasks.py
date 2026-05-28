import logging
from datetime import date

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import Person
from apps.commitments.models import Commitment, CommitmentTag
from apps.meetings.models import Meeting, MeetingTopic, MeetingParticipant, MeetingClarification
from extraction.extractor import extract_commitments, extract_commitments_pass2
from extraction.importer import extract_from_document

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_person(org, name: str):
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
    for label in tag_labels:
        label = label.strip().lower()
        if not label:
            continue
        tag, _ = CommitmentTag.objects.get_or_create(organisation=org, label=label)
        commitment.tags.add(tag)


def _save_topics(meeting, org, topics: list[dict]):
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
    Person.objects.filter(pk=person.pk).update(meeting_count=F('meeting_count') + 1)
    if not person.first_seen_at:
        Person.objects.filter(pk=person.pk).update(first_seen_at=meeting_occurred_at)


def _save_commitments(meeting, org, result: dict) -> int:
    """Persist commitments + participants from an extraction result. Returns count created."""
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

    for speaker_name in result.get("participants", []):
        person = _resolve_person(org, speaker_name)
        if person:
            MeetingParticipant.objects.get_or_create(
                meeting=meeting,
                person=person,
                defaults={'speaker_label': speaker_name, 'confirmed': False},
            )

    return created


# ── Tasks ─────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=2)
def process_meeting(self, meeting_id: str):
    """
    Pass 1 extraction.
    - If Gemini returns clarifications → save them, set PENDING_CLARIFICATION.
      The CoS answers via the API, then process_meeting_pass2 is queued.
    - If no clarifications → save commitments directly, set COMPLETE.
    """
    try:
        meeting = Meeting.objects.select_related('organisation', 'created_by').get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error("process_meeting: meeting %s not found", meeting_id)
        return

    # Guard: already processed — skip to avoid duplicate commitments on double-queue
    if meeting.processing_status == Meeting.ProcessingStatus.COMPLETE:
        logger.info("process_meeting: %s already COMPLETE, skipping", meeting_id)
        return

    meeting.processing_status = Meeting.ProcessingStatus.PROCESSING
    meeting.save(update_fields=['processing_status'])

    notification_args = None  # set inside try, fired outside to avoid retry-on-notify bug
    notification_recipient = meeting.created_by
    try:
        participants = list(meeting.participants.values_list('name', flat=True))
        result = extract_commitments(
            meeting.raw_transcript,
            participants,
            meeting_title=meeting.title,
            meeting_date=meeting.occurred_at.date().isoformat(),
            log_context={'organisation': meeting.organisation, 'meeting_id': meeting.id},
        )

        org = meeting.organisation

        # Always save topics, type, summary from Pass 1 — these don't depend on clarifications
        _save_topics(meeting, org, result["topics"])
        meeting.meeting_type = result["meeting_type"]
        meeting.summary      = result["summary"]
        if not meeting.title and result.get("title"):
            meeting.title = result["title"]

        clarifications = result.get("clarifications", [])
        if clarifications:
            # Delete any stale clarifications from a previous run
            MeetingClarification.objects.filter(meeting=meeting).delete()
            for i, c in enumerate(clarifications):
                MeetingClarification.objects.create(
                    meeting=meeting,
                    question=c["question"],
                    context=c.get("context", ""),
                    order=i,
                )
            meeting.processing_status = Meeting.ProcessingStatus.PENDING_CLARIFICATION
            meeting.save(update_fields=['processing_status', 'meeting_type', 'summary', 'title'])
            logger.info(
                "process_meeting (pass1): %s → %d clarifications needed",
                meeting_id, len(clarifications),
            )
        else:
            # No clarifications — save commitments now and mark complete
            created = _save_commitments(meeting, org, result)
            meeting.processing_status = Meeting.ProcessingStatus.COMPLETE
            meeting.processed_at      = timezone.now()
            meeting.save(update_fields=['processing_status', 'processed_at', 'meeting_type', 'summary', 'title'])
            for participant in meeting.participants.all():
                _update_person_lineage(participant, meeting.occurred_at)
            logger.info(
                "process_meeting (pass1, no clarifications): %s → %d commitments, %d topics, type=%s",
                meeting_id, created, len(result["topics"]), result["meeting_type"],
            )
            notification_args = (
                org, None,
                f'{created} commitment{"s" if created != 1 else ""} extracted from "{meeting.title}" — ready to review.',
                'meeting_ready',
            )

    except Exception as exc:
        logger.error("process_meeting: failed for %s: %s", meeting_id, exc)
        meeting.processing_status = Meeting.ProcessingStatus.FAILED
        meeting.processing_error  = str(exc)[:2000]
        meeting.save(update_fields=['processing_status', 'processing_error'])
        try:
            raise self.retry(exc=exc, countdown=30)
        except MaxRetriesExceededError:
            notification_args = (
                meeting.organisation, None,
                f'Processing failed for "{meeting.title}". Check the meeting in the app for details.',
                'meeting_failed',
            )

    if notification_args:
        try:
            from apps.notifications.views import create_cos_notification
            create_cos_notification(*notification_args, recipient_user=notification_recipient)
        except Exception as exc:
            logger.warning("process_meeting: notification failed for %s: %s", meeting_id, exc)


@shared_task(bind=True, max_retries=2)
def process_meeting_pass2(self, meeting_id: str):
    """
    Pass 2 extraction — runs after CoS has answered all clarifications.
    Sends answered clarifications as context to Gemini, then saves commitments.
    """
    try:
        meeting = Meeting.objects.select_related('organisation', 'created_by').get(id=meeting_id)
    except Meeting.DoesNotExist:
        logger.error("process_meeting_pass2: meeting %s not found", meeting_id)
        return

    # Guard: already processed — skip to avoid duplicate commitments on double-queue
    if meeting.processing_status == Meeting.ProcessingStatus.COMPLETE:
        logger.info("process_meeting_pass2: %s already COMPLETE, skipping", meeting_id)
        return

    meeting.processing_status = Meeting.ProcessingStatus.PROCESSING
    meeting.save(update_fields=['processing_status'])

    notification_args = None
    notification_recipient = meeting.created_by
    try:
        clarifications = list(
            meeting.clarifications.values('question', 'answer').order_by('order')
        )
        participants = list(meeting.participants.values_list('name', flat=True))

        result = extract_commitments_pass2(
            meeting.raw_transcript,
            participants,
            clarifications=clarifications,
            meeting_title=meeting.title,
            meeting_date=meeting.occurred_at.date().isoformat(),
            log_context={'organisation': meeting.organisation, 'meeting_id': meeting.id},
        )

        org = meeting.organisation

        # Update topics/type/summary with pass2 results (may be richer)
        _save_topics(meeting, org, result["topics"])
        meeting.meeting_type = result["meeting_type"]
        meeting.summary      = result["summary"]
        if not meeting.title and result.get("title"):
            meeting.title = result["title"]

        created = _save_commitments(meeting, org, result)

        meeting.processing_status = Meeting.ProcessingStatus.COMPLETE
        meeting.processed_at      = timezone.now()
        meeting.save(update_fields=['processing_status', 'processed_at', 'meeting_type', 'summary', 'title'])

        for participant in meeting.participants.all():
            _update_person_lineage(participant, meeting.occurred_at)

        logger.info(
            "process_meeting_pass2: %s → %d commitments, %d topics, type=%s",
            meeting_id, created, len(result["topics"]), result["meeting_type"],
        )
        notification_args = (
            org, None,
            f'{created} commitment{"s" if created != 1 else ""} extracted from "{meeting.title}" — ready to review.',
            'meeting_ready',
        )

    except Exception as exc:
        logger.error("process_meeting_pass2: failed for %s: %s", meeting_id, exc)
        meeting.processing_status = Meeting.ProcessingStatus.FAILED
        meeting.processing_error  = str(exc)[:2000]
        meeting.save(update_fields=['processing_status', 'processing_error'])
        try:
            raise self.retry(exc=exc, countdown=30)
        except MaxRetriesExceededError:
            notification_args = (
                meeting.organisation, None,
                f'Processing failed for "{meeting.title}". Check the meeting in the app for details.',
                'meeting_failed',
            )

    if notification_args:
        try:
            from apps.notifications.views import create_cos_notification
            create_cos_notification(*notification_args, recipient_user=notification_recipient)
        except Exception as exc:
            logger.warning("process_meeting_pass2: notification failed for %s: %s", meeting_id, exc)


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
        result = extract_from_document(
            meeting.raw_transcript,
            log_context={'organisation': meeting.organisation, 'meeting_id': meeting.id},
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
                source=Commitment.Source.IMPORT,
                status=Commitment.Status.PENDING_REVIEW,
            )
            _save_tags(commitment, org, item.get('tags', []))
            created += 1

        if not meeting.title and result.get("title"):
            meeting.title = result["title"]
        meeting.processing_status = Meeting.ProcessingStatus.COMPLETE
        meeting.processed_at      = timezone.now()
        meeting.save(update_fields=['processing_status', 'processed_at', 'title'])
        logger.info("process_import: %s → %d commitments created", meeting_id, created)

    except Exception as exc:
        logger.error("process_import: failed for %s: %s", meeting_id, exc)
        meeting.processing_status = Meeting.ProcessingStatus.FAILED
        meeting.processing_error  = str(exc)[:2000]
        meeting.save(update_fields=['processing_status', 'processing_error'])
        raise self.retry(exc=exc, countdown=30)
