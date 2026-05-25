import uuid
from django.conf import settings
from django.db import models
from apps.accounts.models import Organisation, Person


class Meeting(models.Model):
    """
    One Meeting per transcript upload or prior-commitments import session.
    processing_status tracks the async Celery pipeline state.
    The frontend polls /meetings/{id}/status/ until complete.

    Week 3.5: meeting_type and summary are populated by the extraction pipeline.
    """

    class Platform(models.TextChoices):
        ZOOM   = 'zoom',   'Zoom'
        UPLOAD = 'upload', 'Manual Upload'
        IMPORT = 'import', 'Prior Commitments Import'

    class ProcessingStatus(models.TextChoices):
        PENDING_PARTICIPANTS  = 'pending_participants',  'Awaiting Participant Validation'
        PENDING               = 'pending',               'Pending'
        PROCESSING            = 'processing',            'Processing'
        PENDING_CLARIFICATION = 'pending_clarification', 'Awaiting Clarification'
        COMPLETE              = 'complete',              'Complete'
        FAILED                = 'failed',                'Failed'

    class MeetingType(models.TextChoices):
        LEADERSHIP = 'leadership', 'Leadership / Exec'
        ONE_ON_ONE = 'one_on_one', '1:1'
        TEAM       = 'team',       'Team standup / sync'
        PROJECT    = 'project',    'Project / workstream'
        BOARD      = 'board',      'Board / governance'
        EXTERNAL   = 'external',   'External / client'
        OTHER      = 'other',      'Other'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='meetings')
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='owned_meetings',
    )
    title        = models.CharField(max_length=500)
    platform     = models.CharField(max_length=20, choices=Platform.choices, default=Platform.UPLOAD)
    occurred_at  = models.DateTimeField()

    # Week 3.5 — AI-classified meeting category and digest
    meeting_type = models.CharField(
        max_length=20, choices=MeetingType.choices,
        default=MeetingType.OTHER, blank=True,
    )
    summary = models.TextField(blank=True)

    participants = models.ManyToManyField(
        Person,
        through='MeetingParticipant',
        related_name='meetings'
    )

    raw_transcript = models.TextField(blank=True)
    source_file    = models.FileField(upload_to='meeting_files/', null=True, blank=True)
    word_count     = models.IntegerField(default=0)

    processing_status = models.CharField(
        max_length=25,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    processed_at     = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    # Zoom metadata (blank for manual uploads)
    external_id  = models.CharField(max_length=255, blank=True)
    external_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.occurred_at.date()})"

    class Meta:
        db_table = 'meetings_meeting'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['organisation', 'occurred_at']),
            models.Index(fields=['organisation', 'processing_status']),
            models.Index(fields=['organisation', 'platform']),
            models.Index(fields=['organisation', 'meeting_type']),
        ]


class MeetingParticipant(models.Model):
    """Through table for Meeting ↔ Person M2M. Not used for IMPORT meetings."""
    meeting       = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    person        = models.ForeignKey(Person, on_delete=models.CASCADE)
    speaker_label = models.CharField(max_length=50, blank=True)
    confirmed     = models.BooleanField(default=False)

    class Meta:
        db_table = 'meetings_meetingparticipant'
        unique_together = [['meeting', 'person']]


class MeetingTopic(models.Model):
    """
    Thematic topics extracted from a meeting transcript alongside the commitment
    extraction pass. 2–5 topics per meeting. These are the node vocabulary for
    the Phase 2 person-centric knowledge graph.

    Deduplication at save time: use get_or_create on (label, meeting, organisation).
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='topics')
    meeting      = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='topics')
    label        = models.CharField(max_length=255)
    confidence   = models.FloatField(default=1.0)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.meeting.title})"

    class Meta:
        db_table = 'meetings_meetingtopic'
        indexes = [
            models.Index(fields=['organisation', 'label']),
            models.Index(fields=['meeting']),
        ]



class MeetingClarification(models.Model):
    """
    A question Gemini raised during Pass 1 extraction that the CoS must answer
    before Pass 2 (final commitment extraction) can run.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting     = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='clarifications')
    question    = models.TextField()
    context     = models.TextField(blank=True)
    answer      = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'meetings_meetingclarification'
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order + 1} for {self.meeting.title}"


class PipelineStatus(Meeting):
    """Proxy used solely to add a Pipeline Status link to the Django admin sidebar."""
    class Meta:
        proxy               = True
        verbose_name        = 'Pipeline Status'
        verbose_name_plural = '⚙ Pipeline Status'
