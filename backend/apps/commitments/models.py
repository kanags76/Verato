import uuid
from django.db import models
from django.utils import timezone
from apps.accounts.models import Organisation, Person
from apps.meetings.models import Meeting


class CommitmentTag(models.Model):
    """
    Thematic tags applied to individual commitments. Deduplicated per org —
    one record shared across all commitments with the same label.
    These are the edges in the Phase 2 person knowledge graph.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='commitment_tags')
    label        = models.CharField(max_length=255)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label

    class Meta:
        db_table = 'commitments_commitmenttag'
        unique_together = [['organisation', 'label']]
        indexes = [
            models.Index(fields=['organisation', 'label']),
        ]


class Commitment(models.Model):
    """
    THE core entity. Lifecycle:
        PENDING_REVIEW → ACTIVE → AT_RISK → ESCALATED
                               ↘              ↘
                             DEFERRED       DELIVERED / CANCELLED

    risk_score recomputed every 6h by Celery. See commitments/risk.py.
    Phase 2 additions (not in schema): embedding, dependencies, superseded_by.
    """

    class CommitType(models.TextChoices):
        EXPLICIT = 'explicit', 'Explicit'

    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        ACTIVE         = 'active',         'Active'
        AT_RISK        = 'at_risk',        'At Risk'
        ESCALATED      = 'escalated',      'Escalated'
        DELIVERED      = 'done',           'Done'
        DEFERRED       = 'deferred',       'Deferred'
        CANCELLED      = 'cancelled',      'Cancelled'

    class Priority(models.TextChoices):
        HIGH   = 'high',   'High (P1)'
        MEDIUM = 'medium', 'Medium (P2)'
        LOW    = 'low',    'Low (P3)'

    class Source(models.TextChoices):
        TRANSCRIPT = 'transcript', 'Extracted from transcript'
        IMPORT     = 'import',     'Imported from prior tracker'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='commitments')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    raw_text        = models.TextField()
    normalised_text = models.TextField()
    commit_type     = models.CharField(max_length=20, choices=CommitType.choices, default=CommitType.EXPLICIT)
    confidence      = models.FloatField()

    owner             = models.ForeignKey(
        Person, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='owned_commitments'
    )
    deadline          = models.DateField(null=True, blank=True)
    deadline_inferred = models.BooleanField(default=False)

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='commitments')
    source  = models.CharField(max_length=20, choices=Source.choices, default=Source.TRANSCRIPT)

    # Week 3.5 — thematic tags; edges for the Phase 2 knowledge graph
    tags = models.ManyToManyField(CommitmentTag, blank=True, related_name='commitments')

    priority   = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    risk_score = models.FloatField(default=0.0)

    reviewed_by = models.ForeignKey(
        Person, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_commitments'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    resolved_at       = models.DateTimeField(null=True, blank=True)
    resolution_note   = models.TextField(blank=True)
    resolution_source = models.TextField(blank=True)

    def is_overdue(self):
        return (
            self.deadline
            and self.deadline < timezone.now().date()
            and self.status not in [
                self.Status.DELIVERED,
                self.Status.CANCELLED,
                self.Status.DEFERRED,
            ]
        )

    def __str__(self):
        return f"{self.normalised_text[:80]} ({self.status})"

    class Meta:
        db_table = 'commitments_commitment'
        ordering = ['deadline', '-risk_score']
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['organisation', 'deadline']),
            models.Index(fields=['owner', 'deadline']),
            models.Index(fields=['organisation', 'risk_score']),
            models.Index(fields=['meeting']),
            models.Index(fields=['organisation', 'source']),
            models.Index(fields=['organisation', 'priority']),
        ]


class EscalationEvent(models.Model):
    """Immutable log of every escalation. Populates the history log on commitment detail."""

    class Method(models.TextChoices):
        SLACK  = 'slack',  'Slack'
        EMAIL  = 'email',  'Email'
        MANUAL = 'manual', 'Manual (in-app)'
        AUTO   = 'auto',   'Automatic (risk score)'

    class Outcome(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        RESPONDED = 'responded', 'Owner responded'
        RESOLVED  = 'resolved',  'Commitment resolved'
        ESCALATED = 'escalated', 'Further escalated'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment   = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='escalations')
    escalated_by = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name='escalations_sent')
    escalated_to = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name='escalations_received')
    method       = models.CharField(max_length=20, choices=Method.choices)
    message_sent = models.TextField(blank=True)
    outcome      = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.PENDING)
    occurred_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_escalationevent'
        ordering = ['-occurred_at']


class ExtractionFeedback(models.Model):
    """
    Every CoS confirm/reject stored as an immutable signal.
    Not acted on in MVP — accumulated for Phase 2 org calibration.
    """

    class FeedbackType(models.TextChoices):
        CONFIRMED   = 'confirmed',   'Confirmed — real commitment'
        REJECTED    = 'rejected',    'Rejected — not a commitment'
        WRONG_OWNER = 'wrong_owner', 'Wrong owner attributed'
        WRONG_DATE  = 'wrong_date',  'Deadline was wrong'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment    = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='feedback')
    organisation  = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FeedbackType.choices)
    note          = models.TextField(blank=True)
    given_by      = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True)
    from_import   = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_extractionfeedback'
        ordering = ['-created_at']
