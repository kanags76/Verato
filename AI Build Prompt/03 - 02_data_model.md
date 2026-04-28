# Commitment OS — Data Model

> **Database:** PostgreSQL 16 with pgvector extension  
> **ORM:** Django 5.x  
> **Multi-tenancy:** All models scoped to `Organisation` via FK  
> **Vector dimensions:** 768 (Gemini text-embedding-004)

---

## 1. Design Principles

- **Commitment is the atom** — every feature is computed from the Commitment object; get this schema right before anything else
- **Organisation scoping on every model** — enforced at the QuerySet level in Django views; no data leaks between tenants
- **State machine for commitment lifecycle** — status transitions are validated server-side, never set arbitrarily
- **pgvector in the same Postgres instance** — no separate vector database; embeddings stored alongside relational data
- **Feedback loop built in** — ExtractionFeedback model accumulates CoS signals to improve extraction over time

---

## 2. Entity Relationship Overview

```
Organisation
    │
    ├── Person (users and tracked participants)
    │       └── MeetingParticipant (M2M through)
    │
    ├── Meeting
    │       └── MeetingParticipant (M2M through)
    │
    ├── Commitment  ◄─── core entity
    │       ├── owner → Person
    │       ├── meeting → Meeting
    │       ├── dependencies → Commitment (self M2M)
    │       ├── superseded_by → Commitment (self FK)
    │       ├── embedding → vector(768)  [pgvector]
    │       └── conflicts → Conflict
    │
    ├── Conflict
    │       ├── commitment_a → Commitment
    │       └── commitment_b → Commitment
    │
    ├── EscalationEvent
    │       └── commitment → Commitment
    │
    ├── ExtractionFeedback
    │       └── commitment → Commitment
    │
    └── OrgCalibration (one-to-one with Organisation)
```

---

## 3. Django Models

### 3.1 accounts/models.py

```python
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class Organisation(models.Model):
    """
    Top-level tenant. Every other model has an org FK.
    All QuerySets filter by org — enforced in base ViewSet.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=255)
    slug       = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settings   = models.JSONField(default=dict)
    # settings keys:
    # - confidence_threshold: float (default 0.65)
    # - nudge_hours_before: int (default 48)
    # - digest_day: str (default "monday")
    # - digest_hour: int (default 7)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'accounts_organisation'


class User(AbstractUser):
    """
    Extended Django user. One user can belong to one org (Phase 1).
    Multi-org support is a Phase 3 consideration.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users'
    )

    class Meta:
        db_table = 'accounts_user'


class Person(models.Model):
    """
    Represents anyone who appears in meetings — may or may not have a User account.
    Users who log in have person.user set. External participants do not.
    Delivery metrics are computed by Celery and stored here for fast reads.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='persons')
    user         = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='person'
    )
    name         = models.CharField(max_length=255)
    email        = models.EmailField(blank=True)
    role         = models.CharField(max_length=255, blank=True)

    # Integration IDs
    slack_user_id  = models.CharField(max_length=64, blank=True)
    zoom_user_id   = models.CharField(max_length=64, blank=True)
    teams_user_id  = models.CharField(max_length=64, blank=True)

    # Computed delivery metrics — updated by weekly Celery task
    delivery_rate          = models.FloatField(default=1.0)  # 0.0–1.0
    avg_days_late          = models.FloatField(default=0.0)
    total_commitments      = models.IntegerField(default=0)
    delivery_rate_updated  = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.organisation.slug})"

    class Meta:
        db_table = 'accounts_person'
        unique_together = [['organisation', 'email']]
        indexes = [
            models.Index(fields=['organisation', 'slack_user_id']),
        ]
```

---

### 3.2 meetings/models.py

```python
import uuid
from django.db import models
from apps.accounts.models import Organisation, Person


class Meeting(models.Model):
    """
    Represents a single meeting. Transcripts stored in S3;
    raw_transcript holds the text for extraction processing.
    processing_status tracks the async Celery pipeline state.
    """

    class Platform(models.TextChoices):
        ZOOM   = 'zoom',   'Zoom'
        TEAMS  = 'teams',  'Microsoft Teams'
        MEET   = 'meet',   'Google Meet'
        UPLOAD = 'upload', 'Manual Upload'

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
    duration_sec = models.IntegerField(null=True, blank=True)

    # Participants — resolved at ingestion time from transcript diarisation
    participants = models.ManyToManyField(
        Person,
        through='MeetingParticipant',
        related_name='meetings'
    )

    # Meeting classification — learned per org over time
    meeting_type = models.CharField(max_length=100, blank=True)
    # e.g. 'leadership_review', 'standup', 'project_review', 'all_hands'

    # Transcript content
    raw_transcript    = models.TextField(blank=True)
    transcript_file   = models.FileField(upload_to='transcripts/%Y/%m/', null=True, blank=True)
    word_count        = models.IntegerField(default=0)

    # Processing state
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    processed_at    = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    # Source platform metadata
    external_id      = models.CharField(max_length=255, blank=True)  # Zoom meeting ID
    external_url     = models.URLField(blank=True)                    # Recording URL

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.occurred_at.date()})"

    class Meta:
        db_table = 'meetings_meeting'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['organisation', 'occurred_at']),
            models.Index(fields=['organisation', 'processing_status']),
        ]


class MeetingParticipant(models.Model):
    """
    Through table for Meeting ↔ Person M2M.
    Tracks how each person was identified in the transcript.
    speaker_label is the diarisation label ('Speaker 1') before resolution.
    """
    meeting      = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    person       = models.ForeignKey(Person, on_delete=models.CASCADE)
    speaker_label = models.CharField(max_length=50, blank=True)  # 'Speaker 1' etc.
    confirmed     = models.BooleanField(default=False)  # human confirmed identity

    class Meta:
        db_table = 'meetings_meetingparticipant'
        unique_together = [['meeting', 'person']]
```

---

### 3.3 commitments/models.py

```python
import uuid
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField
from apps.accounts.models import Organisation, Person
from apps.meetings.models import Meeting


class Commitment(models.Model):
    """
    THE core entity of the system. Every other feature is computed from this.

    Lifecycle:
    PENDING_REVIEW → ACTIVE → AT_RISK → ESCALATED → DELIVERED
                                      ↓            ↓
                                   DEFERRED     CANCELLED

    risk_score is a float 0.0–1.0 computed by commitments/risk.py.
    embedding is a 768-dimension vector (Gemini text-embedding-004)
    used for cross-meeting conflict detection via pgvector cosine similarity.
    """

    class CommitType(models.TextChoices):
        EXPLICIT    = 'explicit',    'Explicit'
        IMPLICIT    = 'implicit',    'Implicit'
        CONDITIONAL = 'conditional', 'Conditional'

    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        ACTIVE         = 'active',         'Active'
        AT_RISK        = 'at_risk',         'At Risk'
        ESCALATED      = 'escalated',       'Escalated'
        DELIVERED      = 'delivered',       'Delivered'
        DEFERRED       = 'deferred',        'Deferred'
        CANCELLED      = 'cancelled',       'Cancelled'

    # Identity
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='commitments')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # What was committed
    raw_text         = models.TextField()           # Exact quote from transcript
    normalised_text  = models.TextField()           # AI-cleaned, owner-resolved version
    commit_type      = models.CharField(max_length=20, choices=CommitType.choices)
    confidence       = models.FloatField()           # 0.0–1.0 extraction confidence
    condition_text   = models.TextField(blank=True)  # For CONDITIONAL type only

    # Who and when
    owner = models.ForeignKey(
        Person, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_commitments'
    )
    mentioned_persons = models.ManyToManyField(
        Person, blank=True,
        related_name='mentioned_in_commitments'
    )
    deadline          = models.DateField(null=True, blank=True)
    deadline_inferred = models.BooleanField(default=False)
    # True when AI inferred deadline from context ('end of week', 'next sprint')

    # Source provenance
    meeting              = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='commitments')
    transcript_offset_sec = models.IntegerField(null=True, blank=True)
    # Approximate position in recording for jump-to-source feature

    # State machine
    status      = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW
    )
    risk_score  = models.FloatField(default=0.0)
    # Recomputed every 6 hours by Celery. See commitments/risk.py for formula.

    reviewed_by = models.ForeignKey(
        Person, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_commitments'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Cross-meeting intelligence
    dependencies = models.ManyToManyField(
        'self', symmetrical=False,
        related_name='dependents', blank=True
    )
    # If dependency is AT_RISK, this commitment's risk_score is inflated.

    superseded_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='supersedes'
    )
    # Set when a later meeting explicitly updates an earlier commitment.

    # pgvector — semantic similarity for conflict detection
    # 768 dimensions = Gemini text-embedding-004 output size
    embedding = VectorField(dimensions=768, null=True, blank=True)

    # Resolution
    resolved_at       = models.DateTimeField(null=True, blank=True)
    resolution_note   = models.TextField(blank=True)
    resolution_source = models.TextField(blank=True)
    # e.g. Slack thread URL, doc link, email reference

    def is_overdue(self):
        return self.deadline and self.deadline < timezone.now().date() and \
               self.status not in [self.Status.DELIVERED, self.Status.CANCELLED, self.Status.DEFERRED]

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
            # pgvector IVFFlat index added via RunSQL in migration:
            # CREATE INDEX ON commitments_commitment
            #   USING ivfflat (embedding vector_cosine_ops)
            #   WITH (lists = 100);
        ]


class Conflict(models.Model):
    """
    Detected contradiction or duplication between two commitments.
    Created by the conflict_detector Celery task after each new commitment is processed.
    Requires CoS review before being surfaced as an active flag.
    """

    class ConflictType(models.TextChoices):
        CONTRADICTION  = 'contradiction',  'Contradiction'
        DUPLICATE      = 'duplicate',      'Duplicate'
        SCOPE_MISMATCH = 'scope_mismatch', 'Scope Mismatch'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='conflicts')

    commitment_a = models.ForeignKey(
        Commitment, on_delete=models.CASCADE, related_name='conflicts_as_a'
    )
    commitment_b = models.ForeignKey(
        Commitment, on_delete=models.CASCADE, related_name='conflicts_as_b'
    )

    conflict_type = models.CharField(max_length=30, choices=ConflictType.choices)
    explanation   = models.TextField()   # Gemini Flash generated — one sentence
    confidence    = models.FloatField()  # 0.0–1.0

    detected_at   = models.DateTimeField(auto_now_add=True)
    resolved      = models.BooleanField(default=False)
    resolved_by   = models.ForeignKey(
        Person, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='resolved_conflicts'
    )
    resolved_at   = models.DateTimeField(null=True, blank=True)
    resolution    = models.TextField(blank=True)

    class Meta:
        db_table = 'commitments_conflict'
        indexes = [
            models.Index(fields=['organisation', 'resolved']),
        ]


class EscalationEvent(models.Model):
    """
    Immutable log of every escalation action taken by the CoS.
    Used for analytics and audit trail.
    """

    class Method(models.TextChoices):
        SLACK   = 'slack',   'Slack'
        EMAIL   = 'email',   'Email'
        MANUAL  = 'manual',  'Manual (in-app)'

    class Outcome(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        RESPONDED = 'responded', 'Owner responded'
        RESOLVED  = 'resolved',  'Commitment resolved'
        ESCALATED = 'escalated', 'Further escalated'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment    = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='escalations')
    escalated_by  = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name='escalations_sent')
    escalated_to  = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name='escalations_received')
    method        = models.CharField(max_length=20, choices=Method.choices)
    framing       = models.CharField(max_length=20, blank=True)
    # 'gentle' | 'urgent' | 'ceo' — selected by CoS in the escalation modal
    message_sent  = models.TextField(blank=True)
    outcome       = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.PENDING)
    occurred_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_escalationevent'
        ordering = ['-occurred_at']
```

---

### 3.4 commitments/calibration_models.py

```python
import uuid
from django.db import models
from apps.accounts.models import Organisation, Person
from apps.commitments.models import Commitment


class OrgCalibration(models.Model):
    """
    Persistent memory layer for org-specific extraction intelligence.
    Accumulated from ExtractionFeedback signals over time.
    Compiled into a context block injected into every Gemini prompt.

    Active after 10+ feedback signals. Recompiled weekly via Celery Beat.
    """
    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE,
        related_name='calibration'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Phrase signals learned from feedback
    commit_phrases = models.JSONField(default=list)
    # [{"phrase": "action item", "weight": 0.95, "type": "EXPLICIT"},
    #  {"phrase": "let's look at", "weight": -0.4, "type": "NOISE"}]

    non_commit_phrases = models.JSONField(default=list)
    # Phrases that look like commits but aren't at this specific org

    # Meeting type signal weights
    meeting_type_weights = models.JSONField(default=dict)
    # {"leadership_review": 0.9, "all_hands": 0.2, "standup": 0.7}

    # Global confidence threshold for this org (CoS can adjust)
    confidence_threshold = models.FloatField(default=0.65)

    # Free-form prose notes compiled from feedback — injected into prompt as-is
    extraction_notes = models.TextField(blank=True)
    # e.g. "At this org, legal team commitments always need 2x the stated deadline.
    #       Sarah K. often says 'I'll look at that' which is NOT a commitment."

    # Calibration maturity tracking
    feedback_count     = models.IntegerField(default=0)
    meetings_processed = models.IntegerField(default=0)

    class Meta:
        db_table = 'commitments_orgcalibration'


class ExtractionFeedback(models.Model):
    """
    Every CoS confirm/reject stored as immutable signal.
    Celery task recompiles OrgCalibration from this history weekly.
    This is the training signal for org-specific extraction improvement.
    """

    class FeedbackType(models.TextChoices):
        CONFIRMED   = 'confirmed',   'Confirmed — this is a real commitment'
        REJECTED    = 'rejected',    'Rejected — this is NOT a commitment'
        WRONG_OWNER = 'wrong_owner', 'Wrong owner attributed'
        WRONG_DATE  = 'wrong_date',  'Deadline was wrong'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment    = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='feedback')
    organisation  = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FeedbackType.choices)
    note          = models.TextField(blank=True)   # Optional CoS comment
    given_by      = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_extractionfeedback'
        ordering = ['-created_at']
```

---

## 4. Risk Score Computation

```python
# commitments/risk.py
# Deterministic formula — not AI. Predictable and auditable.
# Called by Celery task every 6 hours for all ACTIVE and AT_RISK commitments.

from datetime import date

def compute_risk_score(commitment) -> float:
    """
    Returns float 0.0–1.0.
    Above 0.70 → status becomes AT_RISK
    Above 0.90 → status becomes ESCALATED
    Past deadline → status becomes OVERDUE (always red, overrides score)
    """
    today = date.today()
    score = 0.0

    # --- Component 1: Time pressure (40% weight) ---
    if commitment.deadline:
        days_remaining = (commitment.deadline - today).days
        if days_remaining < 0:
            time_score = 1.0       # overdue
        elif days_remaining == 0:
            time_score = 0.95      # due today
        elif days_remaining <= 1:
            time_score = 0.85      # due tomorrow
        elif days_remaining <= 3:
            time_score = 0.65      # due in 2–3 days
        elif days_remaining <= 7:
            time_score = 0.40      # due this week
        elif days_remaining <= 14:
            time_score = 0.20      # due next week
        else:
            time_score = 0.05      # comfortable runway
    else:
        time_score = 0.30          # no deadline = moderate risk

    score += time_score * 0.40

    # --- Component 2: Owner track record (30% weight) ---
    if commitment.owner:
        owner_risk = 1.0 - commitment.owner.delivery_rate
        # delivery_rate of 0.90 → owner_risk of 0.10 (low risk)
        # delivery_rate of 0.45 → owner_risk of 0.55 (elevated risk)
    else:
        owner_risk = 0.50          # unknown owner = moderate risk

    score += owner_risk * 0.30

    # --- Component 3: Dependency health (20% weight) ---
    dependencies = commitment.dependencies.filter(
        status__in=['active', 'at_risk', 'escalated']
    )
    if dependencies.exists():
        dep_risk = dependencies.aggregate(
            avg=models.Avg('risk_score')
        )['avg'] or 0.0
    else:
        dep_risk = 0.0

    score += dep_risk * 0.20

    # --- Component 4: Update recency (10% weight) ---
    if commitment.updated_at:
        from django.utils import timezone
        days_since_update = (timezone.now() - commitment.updated_at).days
        if days_since_update > 7:
            recency_risk = 0.80    # silence for a week = risky
        elif days_since_update > 3:
            recency_risk = 0.40
        else:
            recency_risk = 0.10
    else:
        recency_risk = 0.50

    score += recency_risk * 0.10

    return min(score, 1.0)


def score_to_status(score: float, deadline, current_status: str) -> str:
    """Determine new status from risk score and deadline."""
    today = date.today()

    # Overdue always wins
    if deadline and deadline < today and current_status not in \
       ['delivered', 'deferred', 'cancelled']:
        return 'escalated'  # treat overdue as escalated for surfacing

    if score >= 0.90:
        return 'escalated'
    elif score >= 0.70:
        return 'at_risk'
    elif current_status in ['at_risk', 'escalated']:
        return 'active'     # recovering — risk dropped
    else:
        return current_status  # no change needed
```

---

## 5. Database Migrations — Key Notes

### Enable pgvector on RDS (run once)
```sql
-- Connect to your RDS instance as superuser
CREATE EXTENSION IF NOT EXISTS vector;
```

### Django migration for vector index
```python
# In the migration file after AddField for embedding:
migrations.RunSQL(
    sql="""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS
        commitments_commitment_embedding_idx
        ON commitments_commitment
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """,
    reverse_sql="DROP INDEX IF EXISTS commitments_commitment_embedding_idx;"
)
# Note: CONCURRENTLY allows index creation without locking the table
# lists = 100 is appropriate for up to ~1M rows; increase for larger datasets
```

---

## 6. Key QuerySet Patterns

```python
# Always used in views — enforces org tenancy
class OrgScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(
            organisation=self.request.user.person.organisation
        )

# Dashboard summary — single query
from django.db.models import Count, Avg, Q

def get_dashboard_summary(org_id):
    from apps.commitments.models import Commitment
    today = date.today()

    return Commitment.objects.filter(
        organisation_id=org_id,
        status__in=['active', 'at_risk', 'escalated', 'pending_review']
    ).aggregate(
        overdue=Count('id', filter=Q(deadline__lt=today)),
        at_risk=Count('id', filter=Q(risk_score__gte=0.7, deadline__gte=today)),
        on_track=Count('id', filter=Q(risk_score__lt=0.7, deadline__gte=today)),
        delivery_rate=Avg(
            'owner__delivery_rate',
            filter=Q(status='delivered')
        )
    )

# Conflict candidates — pgvector cosine similarity
from pgvector.django import CosineDistance

def find_similar_commitments(commitment, org_id, threshold=0.82):
    return Commitment.objects.filter(
        organisation_id=org_id,
        status__in=['active', 'at_risk', 'escalated']
    ).alias(
        distance=CosineDistance('embedding', commitment.embedding)
    ).filter(
        distance__lt=(1 - threshold)
    ).exclude(
        id=commitment.id
    ).order_by('distance')[:5]
```

---

## 7. Full Table List

| Table | Rows at 10 customers | Notes |
|---|---|---|
| `accounts_organisation` | ~10 | One per customer |
| `accounts_user` | ~50 | Platform users (CoS, admins) |
| `accounts_person` | ~500 | All meeting participants tracked |
| `meetings_meeting` | ~2,000 | ~200 meetings/org/month |
| `meetings_meetingparticipant` | ~10,000 | ~5 participants per meeting |
| `commitments_commitment` | ~20,000 | ~10 commits per meeting |
| `commitments_conflict` | ~2,000 | ~10% of commits have a conflict |
| `commitments_escalationevent` | ~500 | Sparse — only escalated items |
| `commitments_extractionfeedback` | ~5,000 | Every CoS confirm/reject |
| `commitments_orgcalibration` | ~10 | One per org |

---

*End of document — feed into VS Code + Claude for Django model implementation*
