import uuid
from django.db import models
from apps.accounts.models import Organisation, Person


class Meeting(models.Model):
    """
    One Meeting per transcript upload or prior-commitments import session.
    processing_status tracks the async Celery pipeline state.
    The frontend polls /meetings/{id}/status/ until complete.
    """

    class Platform(models.TextChoices):
        ZOOM   = 'zoom',   'Zoom'
        UPLOAD = 'upload', 'Manual Upload'
        IMPORT = 'import', 'Prior Commitments Import'

    class ProcessingStatus(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETE   = 'complete',   'Complete'
        FAILED     = 'failed',     'Failed'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='meetings')
    title        = models.CharField(max_length=500)
    platform     = models.CharField(max_length=20, choices=Platform.choices, default=Platform.UPLOAD)
    occurred_at  = models.DateTimeField()

    participants = models.ManyToManyField(
        Person,
        through='MeetingParticipant',
        related_name='meetings'
    )

    raw_transcript = models.TextField(blank=True)
    word_count     = models.IntegerField(default=0)

    processing_status = models.CharField(
        max_length=20,
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
