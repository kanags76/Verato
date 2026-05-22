# Verato — Data Model (MVP Complete)

> **Database:** PostgreSQL 18 (no extensions required for MVP)
> **ORM:** Django 6.x
> **Multi-tenancy:** All models scoped to `Organisation` via FK
> **MVP scope:** No pgvector, no embeddings, no Conflict model, no OrgCalibration model
> **Phase 1 complete:** All models built, migrated, tested — 326 tests passing
> **Phase 2 additions noted inline** — schema is designed to accept them without breaking changes

---

## 1. Design Principles

- **Commitment is the atom** — every feature is computed from the Commitment object
- **Organisation scoping on every model** — enforced at the QuerySet level; no data leaks between tenants
- **State machine for commitment lifecycle** — status transitions validated server-side, never set arbitrarily
- **Feedback loop built in from day one** — ExtractionFeedback logs every confirm/reject; accumulated for Phase 2 calibration
- **Graph foundations baked into Phase 1** — MeetingTopic and CommitmentTag create the node/edge vocabulary for the Phase 2 knowledge graph without adding infrastructure
- **No pgvector in MVP** — embeddings and conflict detection are Phase 2

---

## 2. Entity Relationship Overview

```
Organisation (plan: individual|team)
    │
    ├── User (CoS, admin — is_org_admin gates invite sending)
    │
    ├── Invitation (email invite with 7-day token — Week 6.5)
    │
    ├── Person (all meeting participants — may or may not have a User)
    │       └── MeetingParticipant (M2M through table)
    │
    ├── Meeting (one per transcript upload or import session)
    │       ├── MeetingParticipant
    │       ├── MeetingTopic (Week 3.5 — thematic topics per meeting)
    │       └── PipelineStatus (Week 9 — proxy model; admin sidebar link only, no extra table)
    │
    ├── Commitment  ◄─── core entity
    │       ├── owner → Person
    │       ├── meeting → Meeting
    │       ├── tags → CommitmentTag (M2M — Week 3.5)
    │       ├── escalations → EscalationEvent
    │       └── events → CommitmentEvent (append-only audit log)
    │
    ├── EscalationEvent
    │       └── commitment → Commitment
    │
    ├── CommitmentEvent (Week 8 — append-only audit log)
    │       └── commitment → Commitment
    │
    ├── ExtractionFeedback
    │       └── commitment → Commitment
    │
    └── NudgeLog (Week 6 — prevents double-nudging within 20h)
            └── commitment → Commitment

── Phase 2 additions (not built in MVP) ──────────────────────────
    ├── Conflict (commitment_a, commitment_b, type, confidence)
    ├── OrgCalibration (one-to-one with Organisation)
    ├── Commitment.embedding (vector field — add via migration)
    └── PersonGraph API endpoint (aggregates existing tables)
```

---

## 3. Django Models

### 3.1 accounts/models.py

```python
import secrets
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Organisation(models.Model):
    """
    Top-level tenant. Every other model has an org FK.
    plan distinguishes individual (1 user) from team (many users) accounts.
    settings JSONField stores Slack OAuth token, workspace ID, and nudge config.
    """
    class Plan(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        TEAM       = 'team',       'Team'

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name     = models.CharField(max_length=255)
    slug     = models.SlugField(unique=True)
    plan     = models.CharField(max_length=20, choices=Plan.choices, default=Plan.INDIVIDUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    settings   = models.JSONField(default=dict)
    # settings keys used in MVP:
    # - slack_token: str — per-org bot token from Slack OAuth (overrides global SLACK_BOT_TOKEN)
    # - slack_workspace_id: str
    # - slack_workspace_name: str
    # - confidence_threshold: float (default 0.65)
    # - nudge_hours_before: int (default 48)
    # - digest_day: str (default "monday")
    # - digest_hour: int (default 7)

    class Meta:
        db_table = 'accounts_organisation'


class User(AbstractUser):
    """
    Extended Django user. One user belongs to one org.
    CoS, Programme Manager, and Org Admin all have User accounts.
    Commitment owners do NOT have User accounts — they interact via Slack only.
    is_org_admin gates invite-sending — set True on the registering user,
    False on all invited users.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users'
    )
    is_org_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_user'


class Invitation(models.Model):
    """
    Pending invite sent to a colleague's email address.
    Token is a 32-byte URL-safe random string (expires in 7 days).
    Once accepted, accepted_at is set and is_valid returns False.
    Re-inviting the same email refreshes the token and expiry rather than creating a duplicate.
    unique_together on (organisation, email) enforces one active invite per address per org.
    """
    _TOKEN_EXPIRY_DAYS = 7

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='invitations')
    email        = models.EmailField()
    token        = models.CharField(max_length=64, unique=True)
    invited_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    accepted_at  = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_for(cls, organisation, email, invited_by):
        return cls.objects.create(
            organisation=organisation,
            email=email,
            token=secrets.token_urlsafe(32),
            invited_by=invited_by,
            expires_at=timezone.now() + timedelta(days=cls._TOKEN_EXPIRY_DAYS),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.accepted_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used

    class Meta:
        db_table = 'accounts_invitation'
        unique_together = [['organisation', 'email']]


class Person(models.Model):
    """
    Anyone who appears in meetings — may or may not have a User account.
    Users who log in have person.user set (OneToOne).
    External participants (owners who only respond via Slack) do not.

    slack_user_id is set by the person themselves via POST /persons/{id}/link-slack/
    or by an org admin on their behalf.

    delivery_rate and avg_days_late are recomputed by Celery after each commitment resolves.
    first_seen_at and meeting_count are updated by process_meeting after each run.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='persons')
    user         = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='person'
    )
    name  = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    role  = models.CharField(max_length=255, blank=True)

    slack_user_id = models.CharField(max_length=64, blank=True)
    zoom_user_id  = models.CharField(max_length=64, blank=True)

    delivery_rate         = models.FloatField(default=1.0)
    avg_days_late         = models.FloatField(default=0.0)
    total_commitments     = models.IntegerField(default=0)
    delivery_rate_updated = models.DateTimeField(null=True, blank=True)

    first_seen_at = models.DateTimeField(null=True, blank=True)
    meeting_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_person'
        unique_together = [['organisation', 'email']]
        indexes = [
            models.Index(fields=['organisation', 'slack_user_id']),
            models.Index(fields=['organisation', 'first_seen_at']),
        ]
```

---

### 3.2 meetings/models.py

```python
import uuid
from django.db import models
from apps.accounts.models import Organisation, Person


class Meeting(models.Model):
    class Platform(models.TextChoices):
        ZOOM   = 'zoom',   'Zoom'
        UPLOAD = 'upload', 'Manual Upload'
        IMPORT = 'import', 'Prior Commitments Import'

    class ProcessingStatus(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETE   = 'complete',   'Complete'
        FAILED     = 'failed',     'Failed'

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
    title        = models.CharField(max_length=500)
    platform     = models.CharField(max_length=20, choices=Platform.choices, default=Platform.UPLOAD)
    occurred_at  = models.DateTimeField()  # optional on upload — serializer defaults to timezone.now()
    meeting_type = models.CharField(max_length=20, choices=MeetingType.choices, default=MeetingType.OTHER, blank=True)
    summary      = models.TextField(blank=True)
    participants = models.ManyToManyField(Person, through='MeetingParticipant', related_name='meetings')
    raw_transcript    = models.TextField(blank=True)
    word_count        = models.IntegerField(default=0)
    processing_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING)
    processed_at      = models.DateTimeField(null=True, blank=True)
    processing_error  = models.TextField(blank=True)
    external_id  = models.CharField(max_length=255, blank=True)
    external_url = models.URLField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meetings_meeting'
        ordering = ['-occurred_at']


class MeetingParticipant(models.Model):
    """
    Through table for Meeting ↔ Person M2M.
    speaker_label: the name as spoken in the transcript (e.g. "Sarah K.").
    confirmed: False = auto-linked by Gemini, True = user-validated via link-participants.
    """
    meeting       = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    person        = models.ForeignKey(Person, on_delete=models.CASCADE)
    speaker_label = models.CharField(max_length=50, blank=True)
    confirmed     = models.BooleanField(default=False)

    class Meta:
        db_table = 'meetings_meetingparticipant'
        unique_together = [['meeting', 'person']]


class MeetingTopic(models.Model):
    """Thematic topics extracted from a transcript alongside commitments."""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='topics')
    meeting      = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='topics')
    label        = models.CharField(max_length=255)
    confidence   = models.FloatField(default=1.0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meetings_meetingtopic'


class PipelineStatus(Meeting):
    """Week 9 — proxy model. No extra DB table. Used only to add a Pipeline Status
    sidebar link in Django admin that redirects to the custom pipeline status view."""
    class Meta:
        proxy               = True
        verbose_name        = 'Pipeline Status'
        verbose_name_plural = '⚙ Pipeline Status'
```

---

### 3.3 commitments/models.py

```python
import uuid
from django.db import models
from django.utils import timezone
from apps.accounts.models import Organisation, Person
from apps.meetings.models import Meeting


class CommitmentTag(models.Model):
    """Org-scoped tag vocabulary — one record shared across all commitments with that label."""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='commitment_tags')
    label        = models.CharField(max_length=255)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_commitmenttag'
        unique_together = [['organisation', 'label']]


class Commitment(models.Model):
    """
    THE core entity of the system.
    Lifecycle: PENDING_REVIEW → ACTIVE → AT_RISK → ESCALATED
                                    ↘              ↘ DONE / DEFERRED / CANCELLED
    risk_score recomputed daily by Celery. Tags are the knowledge graph edges.
    Every status change and field edit is logged to CommitmentEvent.
    """
    class CommitType(models.TextChoices):
        EXPLICIT = 'explicit', 'Explicit'

    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        ACTIVE         = 'active',         'Active'
        AT_RISK        = 'at_risk',        'At Risk'
        ESCALATED      = 'escalated',      'Escalated'
        DONE           = 'done',           'Done'
        DEFERRED       = 'deferred',       'Deferred'
        CANCELLED      = 'cancelled',      'Cancelled'

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

    owner             = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_commitments')
    deadline          = models.DateField(null=True, blank=True)
    deadline_inferred = models.BooleanField(default=False)

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='commitments')
    source  = models.CharField(max_length=20, choices=Source.choices, default=Source.TRANSCRIPT)

    tags = models.ManyToManyField(CommitmentTag, blank=True, related_name='commitments')

    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    risk_score = models.FloatField(default=0.0)

    reviewed_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_commitments')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    resolved_at       = models.DateTimeField(null=True, blank=True)
    resolution_note   = models.TextField(blank=True)
    resolution_source = models.TextField(blank=True)

    class Meta:
        db_table = 'commitments_commitment'
        ordering = ['deadline', '-risk_score']


class EscalationEvent(models.Model):
    """Immutable log of every escalation. Method=AUTO created by recompute_risk_scores task."""
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
    """Every CoS confirm/reject stored as an immutable signal for Phase 2 calibration."""
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


class CommitmentEvent(models.Model):
    """
    Append-only audit log for every action on a commitment.
    Written by views on every confirm, reject, resolve, reopen, escalate, nudge, and PATCH.
    old_value / new_value are JSON snapshots for field_edited events.
    Never deleted — this is the source of truth for history.
    """
    class EventType(models.TextChoices):
        CONFIRMED    = 'confirmed',    'Confirmed'
        REJECTED     = 'rejected',     'Rejected'
        RESOLVED     = 'resolved',     'Resolved'
        REOPENED     = 'reopened',     'Reopened'
        ESCALATED    = 'escalated',    'Escalated'
        NUDGED       = 'nudged',       'Nudge sent'
        FIELD_EDITED = 'field_edited', 'Fields edited'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment  = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='events')
    event_type  = models.CharField(max_length=30, choices=EventType.choices)
    actor       = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='commitment_events')
    old_value   = models.JSONField(null=True, blank=True)
    new_value   = models.JSONField(null=True, blank=True)
    note        = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commitments_commitmentevent'
        ordering = ['-occurred_at']
```

---

### 3.4 notifications/models.py

```python
import uuid
from django.db import models
from apps.commitments.models import Commitment


class NudgeLog(models.Model):
    """
    Records every Slack nudge sent. Queried before each send_deadline_nudges run
    to enforce the 20-hour cooldown — prevents double-nudging within the same window.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='nudges')
    nudged_at  = models.DateTimeField(auto_now_add=True)
    channel    = models.CharField(max_length=64, blank=True)  # Slack channel/DM id returned by API

    class Meta:
        db_table = 'notifications_nudgelog'
        ordering = ['-nudged_at']
```

---

## 4. Risk Score Computation

```python
# commitments/risk.py — deterministic formula, no LLM
# Called by recompute_risk_scores Celery task daily at midnight.

def compute_risk_score(commitment) -> float:
    """Returns float 0.0–1.0."""
    today = date.today()
    score = 0.0

    # Component 1: Deadline proximity (50%)
    if commitment.deadline:
        days = (commitment.deadline - today).days
        if days < 0:    time_score = 1.0
        elif days == 0: time_score = 0.95
        elif days <= 1: time_score = 0.85
        elif days <= 3: time_score = 0.65
        elif days <= 7: time_score = 0.40
        elif days <= 14: time_score = 0.20
        else:            time_score = 0.05
    else:
        time_score = 0.30  # no deadline = moderate risk

    score += time_score * 0.50

    # Component 2: Owner delivery rate (35%)
    owner_risk = (1.0 - commitment.owner.delivery_rate) if commitment.owner else 0.50
    score += owner_risk * 0.35

    # Component 3: Update recency (15%)
    days_stale = (timezone.now() - commitment.updated_at).days
    recency_risk = 0.80 if days_stale > 7 else (0.40 if days_stale > 3 else 0.10)
    score += recency_risk * 0.15

    return min(score, 1.0)


def score_to_status(score: float, deadline, current_status: str) -> str:
    """Determine new status from score and deadline."""
    closed = {'done', 'deferred', 'cancelled'}
    if deadline and deadline < date.today() and current_status not in closed:
        return 'escalated'   # overdue always escalates
    if score >= 0.90:
        return 'escalated'
    elif score >= 0.70:
        return 'at_risk'
    elif current_status in ['at_risk', 'escalated']:
        return 'active'      # recovering
    return current_status
```

---

## 5. Sign-Up and Onboarding Flow

### Individual plan

```
POST /auth/register/ {name, email, password, plan: "individual", org_name}
→ Creates: Organisation (plan=individual) + User (is_org_admin=True) + Person
→ Returns: {access, refresh} JWT tokens
→ User connects Slack workspace via GET /slack/oauth/start/
→ User links their own Slack user ID via POST /persons/{id}/link-slack/
```

### Team plan

```
Admin:
  POST /auth/register/ {name, email, password, plan: "team", org_name}
  → Same as individual, but creates a team org
  GET /slack/oauth/start/ → Slack OAuth → bot token stored in org.settings

Inviting colleagues:
  POST /auth/invite/ {email}         (admin only — is_org_admin=True)
  → Creates Invitation with 7-day token
  → Sends email: APP_BASE_URL/invite/?token={token}

Colleague accepts:
  GET  /auth/invite/validate/?token= → {email, org_name}   (public)
  POST /auth/invite/accept/ {token, name, password}
  → Creates User (is_org_admin=False) + Person in the same org
  → Marks invite accepted_at = now
  → Returns: {access, refresh} JWT tokens

Each person links their Slack ID:
  POST /persons/{id}/link-slack/ {slack_user_id}
  → Only own account, or admin can link any person
```

---

## 6. Slack OAuth Architecture

```
org.settings = {
    "slack_token":          "xoxb-...",   # per-org bot token from OAuth
    "slack_workspace_id":   "T01234...",
    "slack_workspace_name": "Acme Corp",
}

_get_client(org=None):
    1. Try org.settings['slack_token']      ← per-org (from OAuth)
    2. Fall back to SLACK_BOT_TOKEN env var  ← global fallback / dev
    3. Return None if neither is set (no-op, logs warning)
```

---

## 7. Key QuerySet Patterns

```python
# Organisation-scoped base (enforces tenancy on every query)
class OrgScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(organisation=self.request.user.organisation)


# Dashboard summary — single aggregate query
def get_dashboard_summary(org_id):
    today = date.today()
    active_statuses = ['active', 'at_risk', 'escalated', 'pending_review']
    return Commitment.objects.filter(
        organisation_id=org_id, status__in=active_statuses
    ).aggregate(
        overdue    = Count('id', filter=Q(deadline__lt=today)),
        at_risk    = Count('id', filter=Q(risk_score__gte=0.7, deadline__gte=today)),
        on_track   = Count('id', filter=Q(risk_score__lt=0.7)),
        total_active = Count('id'),
    )


# Nudge candidates — commitments due within 48h with Slack, not recently nudged
def get_nudge_candidates():
    cutoff       = date.today() + timedelta(hours=48)
    cooldown_after = timezone.now() - timedelta(hours=20)
    return Commitment.objects.filter(
        status__in=['active', 'at_risk'],
        deadline__lte=cutoff, deadline__gte=date.today(),
        owner__slack_user_id__gt='',
    ).select_related('owner').exclude(nudges__nudged_at__gte=cooldown_after)


# Person timeline — chronological meetings + commitments + topics
def get_person_timeline(person_id, org_id):
    return (
        Meeting.objects
        .filter(organisation_id=org_id, participants__id=person_id, processing_status='complete')
        .prefetch_related(
            'topics',
            Prefetch('commitments',
                queryset=Commitment.objects.filter(owner_id=person_id).prefetch_related('tags'),
                to_attr='person_commitments')
        )
        .order_by('occurred_at')
    )
```

---

## 8. Extraction Output Schema

Both extraction functions return the same dict format. Keys are normalised by the parser:

```json
{
  "commitments": [
    {
      "raw_text":          "verbatim quote from transcript",
      "normalised_text":   "Sarah K. will send pricing deck by Thursday 30 Apr",
      "commit_type":       "explicit",
      "owner_name":        "Sarah K.",
      "deadline_text":     "end of Thursday",
      "deadline_resolved": "2026-04-30",
      "confidence":        0.94,
      "tags":              ["q2 board prep", "pricing"]
    }
  ],
  "topics": [
    {"label": "q2 board prep", "confidence": 0.96},
    {"label": "emea pricing",  "confidence": 0.91}
  ],
  "meeting_type": "leadership",
  "summary":      "Leadership team reviewed Q2 board deck progress..."
}
```

Note: Import meetings return `"topics": []`, `"meeting_type": "import"`, `"summary": ""`.

---

## 9. Full MVP Table List

| Table | Notes |
|---|---|
| `accounts_organisation` | One per tenant; plan + settings JSONField |
| `accounts_user` | CoS + invited users; is_org_admin gates invites |
| `accounts_invitation` | 7-day tokens; unique_together (org, email) |
| `accounts_person` | All meeting participants; linked to User via OneToOne |
| `meetings_meeting` | Transcripts + imports; meeting_type + summary |
| `meetings_meetingparticipant` | Through table for Meeting ↔ Person |
| `meetings_meetingtopic` | Topics per meeting extracted by Gemini |
| `commitments_commitmenttag` | Org-scoped tag vocabulary; get_or_create on save |
| `commitments_commitment` | Core entity; status machine; risk_score daily; `done` replaces `delivered` |
| `commitments_commitment_tags` | M2M join — ~2 tags per commitment |
| `commitments_escalationevent` | Immutable log; Method=AUTO for Celery escalations |
| `commitments_extractionfeedback` | Every confirm/reject; Phase 2 calibration input |
| `commitments_commitmentevent` | Append-only audit log; every action + field edit written here |
| `notifications_nudgelog` | One record per nudge sent; enforces 20h cooldown |

**Deferred to Phase 2:**

| Table | Why deferred |
|---|---|
| `commitments_conflict` | Requires pgvector + embeddings |
| `commitments_orgcalibration` | Needs 10+ feedback signals; recompilation is Phase 2 |
| PersonGraph rendered view | Data exists in MVP; graph rendering is Phase 2 frontend |

---

## 10. Migrations

| Migration | Contents |
|---|---|
| `accounts/0001_initial` | Organisation, User, Person |
| `accounts/0002_person_lineage` | Person.first_seen_at, Person.meeting_count |
| `accounts/0003_plan_admin_invitation` | Organisation.plan, User.is_org_admin, Invitation model |
| `meetings/0001_initial` | Meeting, MeetingParticipant |
| `meetings/0002_meeting_type_summary` | Meeting.meeting_type, Meeting.summary, MeetingTopic |
| `meetings/0003_meeting_pending_participants_status` | ProcessingStatus.PENDING_PARTICIPANTS choice |
| `meetings/0004_add_pipelinestatus_proxy` | PipelineStatus proxy model (Week 9 — no new table) |
| `commitments/0001_initial` | Commitment, EscalationEvent, ExtractionFeedback |
| `commitments/0002_tags` | CommitmentTag, Commitment.tags M2M |
| `commitments/0003_priority` | Commitment.priority field (high/medium/low) |
| `commitments/0004_commitment_status_done` | Rename status `delivered` → `done`; RunPython data backfill |
| `commitments/0005_commitmentevent` | CommitmentEvent audit log model |
| `notifications/0001_initial` | NudgeLog |

### No pgvector in MVP

When Phase 2 conflict detection is built, add pgvector as a separate migration:

```python
# Phase 2 migration — do not create now
migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;")
migrations.AddField(model_name='commitment', name='embedding',
    field=VectorField(dimensions=768, null=True, blank=True))
```

---

*End of document. Phase 1 data model complete — 264 tests passing. Phase 2 additions (embeddings, conflicts, calibration, graph rendering) documented inline.*
