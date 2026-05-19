# Verato — Data Model (MVP)

> **Database:** PostgreSQL 18 (no extensions required for MVP)
> **ORM:** Django 6.x
> **Multi-tenancy:** All models scoped to `Organisation` via FK
> **MVP scope:** No pgvector, no embeddings, no Conflict model, no OrgCalibration model
> **Phase 2 additions noted inline** — schema is designed to accept them without breaking changes

---

## 1. Design Principles

- **Commitment is the atom** — every feature is computed from the Commitment object; get this schema right before anything else
- **Organisation scoping on every model** — enforced at the QuerySet level in Django views; no data leaks between tenants
- **State machine for commitment lifecycle** — status transitions are validated server-side, never set arbitrarily
- **Feedback loop built in from day one** — ExtractionFeedback logs every confirm/reject; not acted on in MVP but accumulated for Phase 2 calibration
- **No pgvector in MVP** — embeddings and conflict detection are Phase 2; adding the vector field later is a non-breaking migration

---

## 2. Entity Relationship Overview (MVP)

```
Organisation
    │
    ├── User (CoS, admin — logs into Verato)
    │
    ├── Person (all meeting participants — may or may not have a User)
    │       └── MeetingParticipant (M2M through table)
    │
    ├── Meeting (one per transcript upload or import session)
    │       └── MeetingParticipant
    │
    ├── Commitment  ◄─── core entity
    │       ├── owner → Person
    │       └── meeting → Meeting
    │
    ├── EscalationEvent
    │       └── commitment → Commitment
    │
    └── ExtractionFeedback
            └── commitment → Commitment

── Phase 2 additions (not built in MVP) ──────────────────
    ├── Conflict (commitment_a, commitment_b, type, confidence)
    ├── OrgCalibration (one-to-one with Organisation)
    └── Commitment.embedding (vector field — add via migration)
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
    All QuerySets filter by org — enforced in OrgScopedViewSet.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=255)
    slug       = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settings   = models.JSONField(default=dict)
    # settings keys used in MVP:
    # - confidence_threshold: float (default 0.65) — below this, extraction items hidden by default
    # - nudge_hours_before: int (default 48) — hours before deadline to send Slack nudge
    # - digest_day: str (default "monday")
    # - digest_hour: int (default 7) — UTC hour for weekly digest

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'accounts_organisation'


class User(AbstractUser):
    """
    Extended Django user. One user belongs to one org (Phase 1).
    The CoS, Programme Manager, and Org Admin all have User accounts.
    Commitment owners do NOT have User accounts — they interact via Slack only.
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
    Anyone who appears in meetings — may or may not have a User account.
    Users who log in have person.user set. External participants (owners who
    only respond via Slack) do not.

    delivery_rate and avg_days_late are recomputed by Celery after each
    commitment resolves. Used as input to risk scoring.
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

    # Integration IDs — populated when Slack/Zoom connected
    slack_user_id = models.CharField(max_length=64, blank=True)
    zoom_user_id  = models.CharField(max_length=64, blank=True)

    # Delivery metrics — recomputed after each commitment closes
    delivery_rate         = models.FloatField(default=1.0)   # 0.0–1.0
    avg_days_late         = models.FloatField(default=0.0)
    total_commitments     = models.IntegerField(default=0)
    delivery_rate_updated = models.DateTimeField(null=True, blank=True)

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
    One Meeting per transcript upload or prior-commitments import session.

    For transcript uploads: platform = UPLOAD or ZOOM, raw_transcript populated.
    For prior imports: platform = IMPORT, raw_transcript contains the pasted document text.

    processing_status tracks the async Celery pipeline state.
    The frontend polls /meetings/{id}/status/ until complete, then
    redirects to the extraction review screen.
    """

    class Platform(models.TextChoices):
        ZOOM   = 'zoom',   'Zoom'
        UPLOAD = 'upload', 'Manual Upload'
        IMPORT = 'import', 'Prior Commitments Import'
        # Phase 2:
        # TEAMS = 'teams', 'Microsoft Teams'
        # MEET  = 'meet',  'Google Meet'

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

    # Transcript / document content
    raw_transcript = models.TextField(blank=True)
    word_count     = models.IntegerField(default=0)

    # Processing state
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    processed_at     = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    # Zoom metadata (populated by webhook, blank for manual uploads)
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
    """
    Through table for Meeting ↔ Person M2M.
    Not used for IMPORT platform meetings — imports have no participant list.
    """
    meeting       = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    person        = models.ForeignKey(Person, on_delete=models.CASCADE)
    speaker_label = models.CharField(max_length=50, blank=True)  # 'Speaker 1' from diarisation
    confirmed     = models.BooleanField(default=False)

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
from apps.accounts.models import Organisation, Person
from apps.meetings.models import Meeting


class Commitment(models.Model):
    """
    THE core entity of the system.

    Lifecycle:
        PENDING_REVIEW → ACTIVE → AT_RISK → ESCALATED
                               ↘              ↘
                             DEFERRED       DELIVERED
                                            CANCELLED

    source field distinguishes transcript-extracted from prior-import commitments.
    risk_score is recomputed every 6 hours by Celery. See commitments/risk.py.

    MVP fields only. Phase 2 additions (not in schema yet):
    - embedding: VectorField(dimensions=768) — for conflict detection
    - dependencies: ManyToManyField('self') — for dependency chain tracking
    - superseded_by: ForeignKey('self') — when a later meeting updates an earlier commitment
    - condition_text: TextField — for CONDITIONAL commit type
    - mentioned_persons: ManyToManyField(Person) — other people referenced in the commitment
    """

    class CommitType(models.TextChoices):
        EXPLICIT = 'explicit', 'Explicit'
        # Phase 2: IMPLICIT, CONDITIONAL

    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        ACTIVE         = 'active',         'Active'
        AT_RISK        = 'at_risk',        'At Risk'
        ESCALATED      = 'escalated',      'Escalated'
        DELIVERED      = 'delivered',      'Delivered'
        DEFERRED       = 'deferred',       'Deferred'
        CANCELLED      = 'cancelled',      'Cancelled'

    class Source(models.TextChoices):
        TRANSCRIPT = 'transcript', 'Extracted from transcript'
        IMPORT     = 'import',     'Imported from prior tracker'

    # Identity
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='commitments')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # What was committed
    raw_text        = models.TextField()
    # For transcript source: verbatim quote. For import source: the original list item text.
    normalised_text = models.TextField()
    # AI-cleaned version with pronouns resolved to names.
    commit_type     = models.CharField(max_length=20, choices=CommitType.choices, default=CommitType.EXPLICIT)
    confidence      = models.FloatField()  # 0.0–1.0 extraction confidence

    # Who and when
    owner             = models.ForeignKey(
        Person, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_commitments'
    )
    deadline          = models.DateField(null=True, blank=True)
    deadline_inferred = models.BooleanField(default=False)
    # True when AI inferred deadline from context e.g. "end of week" → specific date

    # Provenance
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='commitments')
    source  = models.CharField(max_length=20, choices=Source.choices, default=Source.TRANSCRIPT)

    # State machine
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    risk_score = models.FloatField(default=0.0)
    # Recomputed every 6 hours by recompute_risk_scores Celery task.
    # Above 0.70 → AT_RISK. Above 0.90 → ESCALATED.

    # Review
    reviewed_by = models.ForeignKey(
        Person, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_commitments'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Resolution
    resolved_at       = models.DateTimeField(null=True, blank=True)
    resolution_note   = models.TextField(blank=True)
    resolution_source = models.TextField(blank=True)
    # e.g. Slack thread URL, doc link, email reference (CoS can paste this in)

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
        ]


class EscalationEvent(models.Model):
    """
    Immutable log of every escalation action.
    Created when CoS manually escalates, or when risk score auto-triggers ESCALATED.
    Used to populate the history log on the commitment detail screen.
    """

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
    Not acted on in MVP — accumulated for Phase 2 org calibration recompilation.
    Also distinguishes import discards (not a useful extraction signal) from
    transcript rejects (genuine precision signal).
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
    # True when feedback came from import review — excluded from extraction precision metrics
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_extractionfeedback'
        ordering = ['-created_at']
```

---

## 4. Risk Score Computation (MVP)

```python
# commitments/risk.py
# Deterministic formula — no LLM. Predictable and auditable.
# Called by recompute_risk_scores Celery task every 6 hours.
# Dependency health component removed in MVP (no dependency tracking).
# Weights redistributed: time 50%, owner 35%, recency 15%.

from datetime import date

def compute_risk_score(commitment) -> float:
    """
    Returns float 0.0–1.0.
    Above 0.70 → status becomes AT_RISK
    Above 0.90 → status becomes ESCALATED
    Past deadline + not closed → treated as ESCALATED regardless of score
    """
    today = date.today()
    score = 0.0

    # --- Component 1: Time pressure (50% weight) ---
    if commitment.deadline:
        days_remaining = (commitment.deadline - today).days
        if days_remaining < 0:
            time_score = 1.0       # overdue
        elif days_remaining == 0:
            time_score = 0.95      # due today
        elif days_remaining <= 1:
            time_score = 0.85      # due tomorrow
        elif days_remaining <= 3:
            time_score = 0.65      # 2–3 days
        elif days_remaining <= 7:
            time_score = 0.40      # this week
        elif days_remaining <= 14:
            time_score = 0.20      # next week
        else:
            time_score = 0.05      # comfortable
    else:
        time_score = 0.30          # no deadline = moderate risk

    score += time_score * 0.50

    # --- Component 2: Owner delivery rate (35% weight) ---
    if commitment.owner:
        owner_risk = 1.0 - commitment.owner.delivery_rate
    else:
        owner_risk = 0.50          # unknown owner = moderate risk

    score += owner_risk * 0.35

    # --- Component 3: Update recency (15% weight) ---
    if commitment.updated_at:
        from django.utils import timezone
        days_since_update = (timezone.now() - commitment.updated_at).days
        if days_since_update > 7:
            recency_risk = 0.80
        elif days_since_update > 3:
            recency_risk = 0.40
        else:
            recency_risk = 0.10
    else:
        recency_risk = 0.50

    score += recency_risk * 0.15

    return min(score, 1.0)


def score_to_status(score: float, deadline, current_status: str) -> str:
    """Determine new status from risk score and deadline."""
    today = date.today()
    closed = {'delivered', 'deferred', 'cancelled'}

    if deadline and deadline < today and current_status not in closed:
        return 'escalated'   # overdue always escalates

    if score >= 0.90:
        return 'escalated'
    elif score >= 0.70:
        return 'at_risk'
    elif current_status in ['at_risk', 'escalated']:
        return 'active'      # recovering — score dropped below threshold
    else:
        return current_status
```

---

## 5. Key QuerySet Patterns

```python
# Base ViewSet — enforces org tenancy on every query
class OrgScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(
            organisation=self.request.user.person.organisation
        )


# Dashboard summary — single aggregate query
from django.db.models import Count, Q
from datetime import date

def get_dashboard_summary(org_id):
    from apps.commitments.models import Commitment
    today = date.today()
    active_statuses = ['active', 'at_risk', 'escalated', 'pending_review']

    return Commitment.objects.filter(
        organisation_id=org_id,
        status__in=active_statuses
    ).aggregate(
        overdue=Count('id', filter=Q(deadline__lt=today)),
        at_risk=Count('id', filter=Q(risk_score__gte=0.7, deadline__gte=today)),
        on_track=Count('id', filter=Q(risk_score__lt=0.7)),
        total_active=Count('id'),
    )


# Commitments due for nudge — used by send_deadline_nudges task
from datetime import timedelta

def get_nudge_candidates(org_id, hours_before=48):
    nudge_cutoff = date.today() + timedelta(hours=hours_before)
    return Commitment.objects.filter(
        organisation_id=org_id,
        status__in=['active', 'at_risk'],
        deadline=nudge_cutoff,
        owner__slack_user_id__gt='',  # only owners with Slack ID
    ).select_related('owner', 'meeting')


# Commitments for weekly digest
def get_digest_commitments(org_id):
    from django.db.models import Case, When, IntegerField
    today = date.today()
    week_end = today + timedelta(days=7)

    return Commitment.objects.filter(
        organisation_id=org_id,
        status__in=['active', 'at_risk', 'escalated'],
    ).annotate(
        sort_order=Case(
            When(deadline__lt=today, then=0),          # overdue first
            When(risk_score__gte=0.7, then=1),         # at risk second
            default=2,                                  # on track last
            output_field=IntegerField(),
        )
    ).order_by('sort_order', 'deadline').select_related('owner')
```

---

## 6. Migrations — Key Notes

### No pgvector in MVP

The original data model required pgvector setup and a `RunSQL` migration to create the IVFFlat index. This is removed entirely for MVP.

When Phase 2 conflict detection is built, add pgvector as a separate migration:

```python
# Phase 2 migration — do not create now
from pgvector.django import VectorField

class Migration(migrations.Migration):
    dependencies = [('commitments', '0005_previous_migration')]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;"),
        migrations.AddField(
            model_name='commitment',
            name='embedding',
            field=VectorField(dimensions=768, null=True, blank=True),
        ),
        migrations.RunSQL("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
            commitments_commitment_embedding_idx
            ON commitments_commitment
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """),
    ]
```

### CI — no pgvector image needed

The CI workflow uses `postgres:18` (plain), not `pgvector/pgvector:pg18`. This simplifies setup and speeds up CI runs.

---

## 7. Full MVP Table List

| Table | Rows at 10 design partners | Notes |
|---|---|---|
| `accounts_organisation` | ~10 | One per design partner |
| `accounts_user` | ~20 | CoS + admin per org |
| `accounts_person` | ~200 | All meeting participants tracked |
| `meetings_meeting` | ~500 | Transcripts + import sessions |
| `meetings_meetingparticipant` | ~2,500 | ~5 participants per meeting |
| `commitments_commitment` | ~5,000 | ~10 per meeting; includes imports |
| `commitments_escalationevent` | ~500 | Every Slack nudge + manual escalation |
| `commitments_extractionfeedback` | ~4,000 | Every confirm/reject during review |

**Deferred to Phase 2:**

| Table | Why deferred |
|---|---|
| `commitments_conflict` | Requires embeddings + pgvector — not built in MVP |
| `commitments_orgcalibration` | Requires 10+ feedback signals to be useful; recompilation is Phase 2 |

---

## 8. Extraction Output Schema

Both extraction functions return the same JSON structure. The parser saves this into Commitment objects.

### Transcript extraction (`extraction/extractor.py`)

```json
[
  {
    "raw_text": "I'll have the pricing section of the board deck to you by end of Thursday",
    "normalised_text": "Sarah K. will send the pricing section of the board deck by Thursday 30 Apr",
    "commit_type": "explicit",
    "owner_name": "Sarah K.",
    "deadline_text": "end of Thursday",
    "deadline_resolved": "2026-04-30",
    "confidence": 0.94
  }
]
```

### Prior import extraction (`extraction/importer.py`)

```json
[
  {
    "raw_text": "Sarah - Q2 board deck pricing - Apr 30",
    "normalised_text": "Sarah K. to deliver Q2 board deck pricing section",
    "commit_type": "explicit",
    "owner_name": "Sarah",
    "deadline_text": "Apr 30",
    "deadline_resolved": "2026-04-30",
    "confidence": 0.91
  }
]
```

Key differences in import extraction:
- No speaker label resolution (no participant list provided)
- `owner_name` matched against org's Person records by fuzzy name match after extraction
- Confidence reflects document structure clarity, not speech extraction confidence
- Items saved with `source='import'`; `meeting.platform='import'`

---

*End of document. MVP only — Phase 2 additions (embeddings, conflicts, calibration) documented inline as deferred.*
