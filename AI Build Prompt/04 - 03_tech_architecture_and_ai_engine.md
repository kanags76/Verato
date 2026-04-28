# Commitment OS — Technical Architecture & AI Engine

> **Backend:** Django 5.x + DRF — deployed on AWS (ECS Fargate + RDS + ElastiCache)  
> **Frontend:** Next.js 14 (React) — deployed on GCP (Cloud Run)  
> **LLM:** Gemini 1.5 Pro / Flash (Google AI Studio → Vertex AI in Phase 2)  
> **Embeddings:** Gemini text-embedding-004 (768 dimensions, via pgvector)  
> **Communication:** HTTPS only · JWT Bearer auth · JSON responses  
> **Principle:** Zero hard coupling — frontend and backend are independently deployable

---

## 1. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  GOOGLE CLOUD — Frontend Zone                                    │
│                                                                  │
│  ┌─────────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │  Next.js App    │    │  Cloud CDN   │    │  Gemini API    │  │
│  │  Cloud Run      │    │  Static assets    │  AI Studio /   │  │
│  │  SSR + API BFF  │    │              │    │  Vertex AI     │  │
│  └────────┬────────┘    └──────────────┘    └────────────────┘  │
│           │                                        ↑            │
└───────────┼────────────────────────────────────────┼────────────┘
            │ HTTPS · JWT Bearer · JSON               │ Called from
            │                                         │ AWS workers only
┌───────────┼─────────────────────────────────────────┼────────────┐
│  AWS — Backend Zone                                 │            │
│           │                                         │            │
│  ┌────────▼────────┐    ┌──────────────┐            │            │
│  │  AWS ALB        │    │  API Gateway │            │            │
│  │  Load Balancer  │    │  (optional)  │            │            │
│  └────────┬────────┘    └──────────────┘            │            │
│           │                                         │            │
│  ┌────────▼────────┐    ┌──────────────┐    ┌──────┴─────────┐  │
│  │  Django REST    │    │  Celery      │    │  Celery        │  │
│  │  ECS Fargate    │    │  Workers     │    │  AI Pipeline   │  │
│  │  (API only)     │    │  ECS Fargate │    │  ECS Fargate   │  │
│  └────────┬────────┘    └──────┬───────┘    └────────────────┘  │
│           │                   │                                  │
│  ┌────────▼────────────────────▼──────────────────────────────┐  │
│  │                    AWS Services                             │  │
│  │  RDS PostgreSQL 16  │  ElastiCache Redis  │  S3 Transcripts│  │
│  │  (+ pgvector ext)   │  (Celery broker)    │  (file store)  │  │
│  │                     │                     │                │  │
│  │  Secrets Manager    │  ECR                │  CloudWatch    │  │
│  │  (all credentials)  │  (Docker images)    │  (logs)        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. AWS Backend — Service Breakdown

### 2.1 ECS Fargate — Three Task Definitions

All three ECS tasks use the **same Docker image** (built from one `Dockerfile`). The `CMD` is overridden per task.

```yaml
# Task 1: Django API
Name: commitment-os-api
CPU: 1 vCPU | Memory: 2GB
Command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60
Desired count: 1 (scale to 3 under load)
Health check: GET /api/health/ → 200

# Task 2: Celery Worker
Name: commitment-os-worker
CPU: 1 vCPU | Memory: 2GB
Command: celery -A config worker --loglevel=info --concurrency=4 --queues=default,ai_pipeline,notifications
Desired count: 1 (scale to 5 based on queue depth)

# Task 3: Celery Beat (scheduler)
Name: commitment-os-beat
CPU: 0.25 vCPU | Memory: 512MB
Command: celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Desired count: 1 (always exactly 1 — never scale this)
```

### 2.2 RDS PostgreSQL 16

```
Instance:    db.t4g.small (2 vCPU, 2GB RAM)
Storage:     20GB gp3, auto-scaling to 100GB
Multi-AZ:    No (Phase 1) → Yes (Phase 2)
Backups:     Daily automated, 7-day retention
Extensions:  vector (pgvector) — enable on creation
Parameter:   shared_preload_libraries = 'pg_stat_statements'
```

### 2.3 ElastiCache Redis

```
Instance:    cache.t4g.micro (0.5GB)
Engine:      Redis 7.x
Purpose:     Celery broker + result backend + Django cache
Persistence: No (broker data is ephemeral)
```

### 2.4 S3 Bucket — Transcripts

```
Bucket:      commitment-os-transcripts-{env}
Region:      Same as ECS (us-east-1 recommended)
Lifecycle:   Transition to Glacier after 90 days
Encryption:  SSE-S3 (AES-256)
Access:      Private — accessed via django-storages with IAM role
```

### 2.5 Secrets Manager

All credentials stored in Secrets Manager, never in environment files. ECS task execution role has `secretsmanager:GetSecretValue` permission. Secrets injected as environment variables at container startup.

```
commitment-os/prod/django-secret-key
commitment-os/prod/database-url
commitment-os/prod/redis-url
commitment-os/prod/gemini-api-key
commitment-os/prod/slack-bot-token
commitment-os/prod/slack-signing-secret
commitment-os/prod/sendgrid-api-key
commitment-os/prod/zoom-client-id
commitment-os/prod/zoom-client-secret
commitment-os/prod/zoom-webhook-secret
```

---

## 3. GCP Frontend — Cloud Run

```
Service:     commitment-os-frontend
Region:      us-central1 (or closest to your users)
CPU:         1 vCPU
Memory:      512MB
Min instances: 0 (scale to zero when idle)
Max instances: 10
Concurrency: 80 requests per instance
Port:        3000
```

### 3.1 Next.js Architecture

```
Next.js App (Cloud Run)
├── App Router (SSR pages)
│   ├── /dashboard          → CoS command centre
│   ├── /commitments        → Full list + filters
│   ├── /commitments/:id    → Detail + escalation
│   ├── /meetings/upload    → Transcript ingestion
│   ├── /analytics          → Delivery rates + trends
│   └── /conflicts          → Cross-meeting conflicts
│
├── lib/api/client.ts       → All Django API calls (typed)
│   ├── NEXT_PUBLIC_API_URL → https://api.commitment-os.com
│   └── JWT Bearer token    → Added to every request header
│
└── app/api/auth/           → BFF: token refresh proxy only
    └── refresh/route.ts    → Proxies to Django /auth/token/refresh/
```

### 3.2 Frontend Environment Variables

```bash
# Public — safe in browser bundle
NEXT_PUBLIC_API_URL=https://api.commitment-os.com
NEXT_PUBLIC_APP_ENV=production

# Server-side only (Next.js BFF routes)
JWT_COOKIE_SECRET=<random 32-char string>
```

**Rule:** Frontend holds no API keys, no DB credentials, no LLM keys. If someone decompiles the JS bundle, they find nothing sensitive.

---

## 4. Django Project Structure

```
commitment_os/                  ← Django project root
├── config/
│   ├── settings/
│   │   ├── base.py             ← Shared settings
│   │   ├── local.py            ← Dev overrides (DEBUG=True, no S3)
│   │   └── production.py       ← Prod (S3, no DEBUG, real secrets)
│   ├── urls.py                 ← Root URL config
│   ├── wsgi.py
│   └── celery.py               ← Celery app + Beat schedule
│
├── apps/
│   ├── accounts/               ← Org, User, Person
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── meetings/               ← Meeting ingestion
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── tasks.py            ← process_meeting Celery task
│   │   └── connectors/
│   │       ├── zoom.py         ← Zoom OAuth + webhook handler
│   │       └── teams.py        ← Phase 2
│   │
│   ├── commitments/            ← Core domain
│   │   ├── models.py           ← Commitment, Conflict, Escalation, Calibration
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── tasks.py            ← recompute_risk_scores, send_nudges
│   │   ├── risk.py             ← Deterministic risk formula
│   │   └── filters.py          ← DRF filter classes
│   │
│   ├── notifications/          ← Slack, email
│   │   ├── tasks.py
│   │   ├── slack.py            ← Slack Bolt app
│   │   └── email.py            ← Digest templates
│   │
│   └── analytics/              ← Aggregation endpoints
│       ├── views.py
│       └── queries.py
│
├── extraction/                 ← AI pipeline — pure Python, no Django deps
│   ├── extractor.py            ← Main Gemini extraction orchestrator
│   ├── prompt_builder.py       ← Builds prompts with calibration context
│   ├── parser.py               ← Safely parses Gemini JSON responses
│   ├── conflict_detector.py    ← pgvector similarity + Gemini Flash
│   ├── calibration.py          ← Compiles OrgCalibration into prompt context
│   └── tests/
│       ├── test_extractor.py
│       └── fixtures/           ← Sample transcripts for unit tests
│
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── Dockerfile
├── docker-compose.yml          ← Local dev: web, celery, celerybeat, db, redis
├── .env.example
└── manage.py
```

---

## 5. API Architecture — Django REST Framework

### 5.1 CORS & Auth Configuration

```python
# config/settings/base.py

INSTALLED_APPS = [
    # ...
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',          # OpenAPI schema auto-generation
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # MUST be first
    'django.middleware.common.CommonMiddleware',
    # ...
]

# CORS — allow GCP frontend domain only
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
# Production value: ["https://app.commitment-os.com"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['authorization', 'content-type', 'accept', 'x-requested-with']

# JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF defaults
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # No browsable API in production
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'user': '1000/hour'},
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

### 5.2 Full API Endpoint Reference

```
Base URL: https://api.commitment-os.com/api/v1/

AUTH
  POST   /auth/token/              Get JWT access + refresh tokens
  POST   /auth/token/refresh/      Refresh expired access token
  POST   /auth/token/blacklist/     Logout (invalidate refresh token)

DASHBOARD
  GET    /dashboard/               CoS command centre stats

MEETINGS
  POST   /meetings/upload/         Upload transcript file or text (async)
  POST   /meetings/zoom/webhook/   Zoom webhook (not called by frontend)
  GET    /meetings/{id}/status/    Poll async processing status
  GET    /meetings/                List all org meetings

COMMITMENTS
  GET    /commitments/             List with filters
                                   ?status=at_risk,overdue
                                   ?owner={person_id}
                                   ?deadline_before=2026-05-31
                                   ?risk_gte=0.7
  GET    /commitments/{id}/        Detail view
  PATCH  /commitments/{id}/        Update owner, deadline
  POST   /commitments/{id}/confirm/     Confirm pending → active
  POST   /commitments/{id}/escalate/    Trigger escalation
  POST   /commitments/{id}/resolve/     Mark delivered/deferred/cancelled

CONFLICTS
  GET    /conflicts/               List unresolved conflicts
  POST   /conflicts/{id}/resolve/  Resolve a conflict

ANALYTICS
  GET    /analytics/delivery-rates/     Delivery rate by person/team/period
  GET    /analytics/risk-summary/       Risk distribution snapshot
  GET    /analytics/commitment-volume/  Commits made over time

PERSONS
  GET    /persons/                 List org participants (for owner picker)
  GET    /persons/{id}/            Person detail + delivery metrics
```

### 5.3 Response Envelope

```json
// All responses use this structure

// Success — single resource
{
  "status": "success",
  "data": { "id": "...", "normalised_text": "..." }
}

// Success — list
{
  "status": "success",
  "data": [ {...}, {...} ],
  "meta": { "count": 47, "next": "?cursor=abc", "previous": null }
}

// Async accepted
{
  "status": "accepted",
  "data": {
    "meeting_id": "uuid",
    "processing_status": "pending",
    "poll_url": "/api/v1/meetings/uuid/status/"
  }
}

// Error
{
  "status": "error",
  "code": "COMMITMENT_NOT_FOUND",
  "message": "Commitment with id 'abc' not found.",
  "field_errors": {}
}
```

---

## 6. Celery Task Architecture

```python
# config/celery.py

from celery import Celery
from celery.schedules import crontab

app = Celery('commitment_os')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Three named queues — allows worker specialisation later
app.conf.task_routes = {
    'apps.meetings.tasks.*':       {'queue': 'ai_pipeline'},   # LLM calls
    'apps.notifications.tasks.*':  {'queue': 'notifications'}, # Slack/email
    'apps.commitments.tasks.*':    {'queue': 'default'},       # Risk scoring
}

# Celery Beat — scheduled tasks
app.conf.beat_schedule = {
    'recompute-risk-scores': {
        'task': 'apps.commitments.tasks.recompute_risk_scores',
        'schedule': crontab(minute=0, hour='*/6'),   # Every 6 hours
    },
    'send-deadline-nudges': {
        'task': 'apps.notifications.tasks.send_deadline_nudges',
        'schedule': crontab(minute=0, hour=9),       # 09:00 daily
    },
    'send-weekly-digest': {
        'task': 'apps.notifications.tasks.send_weekly_digest',
        'schedule': crontab(minute=0, hour=7, day_of_week='monday'),
    },
    'recompile-org-calibrations': {
        'task': 'apps.commitments.tasks.recompile_all_calibrations',
        'schedule': crontab(minute=0, hour=2, day_of_week='sunday'),
    },
}
```

### Key Celery Tasks

```python
# apps/meetings/tasks.py

@app.task(bind=True, max_retries=3, default_retry_delay=60, queue='ai_pipeline')
def process_meeting(self, meeting_id: str):
    """
    Full async pipeline triggered after every meeting ingestion.
    1. Call Gemini 1.5 Pro → extract commitments
    2. Generate embeddings (Gemini text-embedding-004)
    3. Run conflict detection against existing commitments (pgvector + Gemini Flash)
    4. Save all objects with PENDING_REVIEW status
    5. Notify CoS via Slack/email that commitments are ready to review
    """

# apps/commitments/tasks.py

@app.task(queue='default')
def recompute_risk_scores():
    """
    Runs every 6 hours.
    Updates risk_score and status for all ACTIVE and AT_RISK commitments.
    Uses deterministic formula in commitments/risk.py — no LLM call.
    """

@app.task(queue='notifications')
def send_deadline_nudges():
    """
    Runs at 09:00 daily.
    Sends Slack DM to all owners with commitments due in 48 hours.
    Owner replies ("done" / "delayed" / "blocked") update status via Slack action handler.
    """
```

---

## 7. AI Engine — Gemini Integration

### 7.1 Model Selection Strategy

| Task | Model | Reason |
|---|---|---|
| Commitment extraction | `gemini-1.5-pro` | 1M context = full transcript in one call; highest accuracy |
| Conflict classification | `gemini-1.5-flash` | Binary classification; ~10x cheaper; sufficient accuracy |
| Semantic embeddings | `text-embedding-004` | 768 dims; native GCP; stays on free credits |
| Whisper (audio → text) | `openai/whisper-1` | Only when no native transcript exists; not yet needed in Phase 1 |

### 7.2 Extraction Pipeline (extraction/extractor.py)

```python
import json
import google.generativeai as genai
from django.conf import settings
from .calibration import get_calibration_context
from .parser import parse_extraction_response, safe_json_parse

genai.configure(api_key=settings.GEMINI_API_KEY)

extraction_model     = genai.GenerativeModel("gemini-1.5-pro")
classification_model = genai.GenerativeModel("gemini-1.5-flash")


def extract_commitments(meeting, transcript_text: str, participants: list) -> list[dict]:
    """
    Sends the ENTIRE transcript to Gemini 1.5 Pro in one call.
    No chunking — the 1M token context handles full meetings comfortably.
    A 2-hour meeting is ~15,000 words (~20,000 tokens). Fits many times over.

    Returns list of dicts ready to create as Commitment objects.
    """
    calibration_ctx = get_calibration_context(meeting.organisation)
    participant_str = _format_participants(participants)

    prompt = f"""You are an organisational accountability analyst.
Extract every commitment from this meeting transcript.

DEFINITION:
A commitment is any statement where a named person agrees to deliver a specific
output by a specific or implied time.

COMMITMENT TYPES:
- EXPLICIT: clear owner, output, and deadline all stated directly
  Example: "I'll have the report ready by Friday."
- IMPLICIT: agreement inferred from context — owner and output reasonably clear
  Example: "We agreed to move forward with the vendor selection." (who agreed = who spoke)
- CONDITIONAL: depends on a condition first being met
  Example: "If the budget is approved, Sarah will kick off the hire."

DO NOT extract:
- General discussion points or opinions
- Questions or suggestions without agreement
- Vague intentions ("we should look at this sometime")
- Statements about what already happened (past tense facts)

{calibration_ctx}

MEETING CONTEXT:
Title: {meeting.title}
Date: {meeting.occurred_at.date()}
Type: {meeting.meeting_type or "General"}
Participants: {participant_str}

OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown, no prose, no code fences.
If no commitments found, return [].

[
  {{
    "raw_text": "exact quote from transcript — the actual words spoken",
    "normalised_text": "clean version resolving pronouns to names",
    "commit_type": "EXPLICIT",
    "owner_name": "exact name as appears in participant list",
    "output_description": "what specifically will be delivered",
    "deadline_text": "as stated in transcript e.g. 'end of Thursday'",
    "deadline_resolved": "YYYY-MM-DD or null if cannot be determined",
    "confidence": 0.94,
    "condition_text": "only for CONDITIONAL type — the condition that must be met",
    "transcript_position": "early | middle | late"
  }}
]

TRANSCRIPT:
{transcript_text}
"""

    response = extraction_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.1,                           # Low temp = deterministic
            response_mime_type="application/json",     # Force JSON output mode
            max_output_tokens=8192,
        ),
        safety_settings={                              # Disable safety filters for business content
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
        }
    )

    candidates = safe_json_parse(response.text)
    return _resolve_owners(candidates, participants)


def _format_participants(participants) -> str:
    lines = []
    for p in participants:
        person = p.person
        line = f"- {person.name}"
        if person.role:
            line += f" ({person.role})"
        if p.speaker_label:
            line += f" [transcript label: {p.speaker_label}]"
        lines.append(line)
    return "\n".join(lines)


def _resolve_owners(candidates: list, participants: list) -> list:
    """
    Match owner_name strings from LLM output to actual Person objects.
    Fuzzy match on name — handles "Sarah" matching "Sarah K." etc.
    """
    from difflib import get_close_matches
    person_map = {p.person.name.lower(): p.person for p in participants}
    all_names = list(person_map.keys())

    for c in candidates:
        owner_name = c.get('owner_name', '').lower()
        if owner_name in person_map:
            c['owner_person'] = person_map[owner_name]
        else:
            matches = get_close_matches(owner_name, all_names, n=1, cutoff=0.6)
            c['owner_person'] = person_map[matches[0]] if matches else None

    return candidates
```

### 7.3 Conflict Detection (extraction/conflict_detector.py)

```python
import json
import google.generativeai as genai
from pgvector.django import CosineDistance
from django.conf import settings

classification_model = genai.GenerativeModel("gemini-1.5-flash")


def get_embedding(text: str) -> list[float]:
    """
    Gemini text-embedding-004 — 768 dimensions.
    Used for pgvector cosine similarity search.
    task_type=SEMANTIC_SIMILARITY optimises for meaning comparison.
    """
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="SEMANTIC_SIMILARITY"
    )
    return result['embedding']


def find_conflict_candidates(new_commitment, org_id: str, threshold: float = 0.82) -> list:
    """
    Step 1: Fast pgvector similarity search.
    Returns commitments semantically similar to the new one.
    threshold=0.82 means cosine similarity > 0.82 (distance < 0.18).
    """
    from apps.commitments.models import Commitment

    if new_commitment.embedding is None:
        return []

    return list(
        Commitment.objects.filter(
            organisation_id=org_id,
            status__in=['active', 'at_risk', 'escalated'],
        ).alias(
            distance=CosineDistance('embedding', new_commitment.embedding)
        ).filter(
            distance__lt=(1 - threshold)
        ).exclude(
            id=new_commitment.id
        ).select_related('owner', 'meeting')
        .order_by('distance')[:5]
    )


def classify_conflict(commit_a, commit_b) -> dict | None:
    """
    Step 2: Gemini Flash classifies whether similar commitments actually conflict.
    Returns None if no conflict. Uses Flash for cost efficiency.
    """
    prompt = f"""Two commitments from the same organisation. Classify their relationship.

Commitment A:
Date: {commit_a.meeting.occurred_at.date()}
Quote: "{commit_a.raw_text}"
Owner: {commit_a.owner.name if commit_a.owner else 'Unknown'}
Deadline: {commit_a.deadline}

Commitment B:
Date: {commit_b.meeting.occurred_at.date()}
Quote: "{commit_b.raw_text}"
Owner: {commit_b.owner.name if commit_b.owner else 'Unknown'}
Deadline: {commit_b.deadline}

CLASSIFICATION OPTIONS:
- CONTRADICTION: Same topic but conflicting terms, deadline, or owner
- DUPLICATE: Same commitment stated identically or near-identically
- SCOPE_MISMATCH: Related but one expands/shrinks the scope of the other
- NO_CONFLICT: Different enough that no action required

Return ONLY valid JSON:
{{"conflict_type": "CONTRADICTION", "confidence": 0.87, "explanation": "one sentence max"}}"""

    response = classification_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
            max_output_tokens=200,
        )
    )

    result = json.loads(response.text)
    if result.get("conflict_type") == "NO_CONFLICT":
        return None
    if result.get("confidence", 0) < 0.70:
        return None  # Below confidence threshold — don't surface as conflict

    return result
```

### 7.4 Calibration Context (extraction/calibration.py)

```python
def get_calibration_context(organisation) -> str:
    """
    Compiles OrgCalibration into a prose block injected into every extraction prompt.
    Returns empty string for new orgs (< 10 feedback signals).
    The system gets more accurate over time as CoS confirms/rejects extractions.
    """
    try:
        cal = organisation.calibration
    except Exception:
        return ""

    if cal.feedback_count < 10:
        return ""  # Not enough signal yet

    lines = ["Organisation-specific extraction context (use this to calibrate your output):"]

    # Strong commit indicators
    strong = [p['phrase'] for p in cal.commit_phrases if p.get('weight', 0) > 0.80]
    if strong:
        lines.append(f"Phrases that reliably indicate a commitment at this org: {', '.join(strong)}")

    # Noise phrases — look like commits but aren't
    noise = [p['phrase'] for p in cal.non_commit_phrases if p.get('weight', 0) < -0.30]
    if noise:
        lines.append(f"Phrases that do NOT indicate commitments here: {', '.join(noise)}")

    # Free-form notes
    if cal.extraction_notes:
        lines.append(cal.extraction_notes)

    lines.append(f"Minimum confidence threshold for this org: {cal.confidence_threshold}")

    return "\n".join(lines)
```

### 7.5 Safe JSON Parsing (extraction/parser.py)

```python
import json
import re
from typing import Any


def safe_json_parse(text: str) -> Any:
    """
    Gemini occasionally wraps JSON in markdown code fences despite being asked not to.
    This strips those and handles common formatting issues safely.
    """
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()

    try:
        parsed = json.loads(text)
        # Validate it's a list
        if not isinstance(parsed, list):
            return []
        return parsed
    except json.JSONDecodeError as e:
        # Log the error and return empty — never crash the pipeline
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to parse Gemini extraction response: {e}\nText: {text[:500]}")
        return []
```

---

## 8. Requirements Files

### requirements/base.txt
```
# Core framework
django==5.1
djangorestframework==3.15
django-cors-headers==4.3
djangorestframework-simplejwt==5.3
django-allauth==65.0
django-filter==24.1
drf-spectacular==0.27

# Database
psycopg2-binary==2.9.9
pgvector==0.3.2
django-pgvector==0.3.0

# Async tasks
celery==5.4
redis==5.0
django-celery-beat==2.6
django-celery-results==2.5

# AI / LLM
google-generativeai==0.8.0
google-cloud-aiplatform==1.60.0  # For Vertex AI migration in Phase 2

# Integrations
slack-bolt==1.18
django-anymail[sendgrid]==11.0
django-storages[boto3]==1.14
boto3==1.34
requests==2.31

# Utilities
python-decouple==3.8
gunicorn==22.0
whitenoise==6.7         # Static files in production
sentry-sdk==2.0         # Error tracking
```

### requirements/local.txt
```
-r base.txt
django-debug-toolbar==4.4
factory-boy==3.3        # Test factories
pytest-django==4.8
pytest-celery==1.0
model-bakery==1.19
ipython==8.26
```

### requirements/production.txt
```
-r base.txt
# No additions needed — gunicorn already in base
```

---

## 9. Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

# Application code
COPY . .

# Collect static files (served by whitenoise)
RUN python manage.py collectstatic --noinput --settings=config.settings.production

# Default command — overridden per ECS task definition
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

EXPOSE 8000
```

### docker-compose.yml (local dev)
```yaml
version: '3.9'

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: commitment_os
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  celery:
    build: .
    command: celery -A config worker --loglevel=info --queues=default,ai_pipeline,notifications
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  celerybeat:
    build: .
    command: celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  postgres_data:
```

---

## 10. CI/CD — GitHub Actions

### .github/workflows/deploy-backend.yml
```yaml
name: Deploy Backend to AWS ECS

on:
  push:
    branches: [main]
    paths: ['backend/**', 'Dockerfile', 'requirements/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        run: |
          IMAGE_URI=${{ secrets.ECR_REGISTRY }}/commitment-os:${{ github.sha }}
          docker build -t $IMAGE_URI .
          docker push $IMAGE_URI
          echo "IMAGE_URI=$IMAGE_URI" >> $GITHUB_ENV

      - name: Run Django migrations
        run: |
          aws ecs run-task \
            --cluster commitment-os \
            --task-definition commitment-os-migrate \
            --overrides '{"containerOverrides":[{"name":"app","command":["python","manage.py","migrate","--settings=config.settings.production"]}]}' \
            --wait-for-task-stopped

      - name: Deploy API service
        run: |
          aws ecs update-service \
            --cluster commitment-os \
            --service commitment-os-api \
            --force-new-deployment

      - name: Deploy Celery worker
        run: |
          aws ecs update-service \
            --cluster commitment-os \
            --service commitment-os-worker \
            --force-new-deployment
```

### .github/workflows/deploy-frontend.yml
```yaml
name: Deploy Frontend to GCP Cloud Run

on:
  push:
    branches: [main]
    paths: ['frontend/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Build and push to Artifact Registry
        run: |
          cd frontend
          gcloud builds submit \
            --tag us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/commitment-os/frontend:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy commitment-os-frontend \
            --image us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/commitment-os/frontend:${{ github.sha }} \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars NEXT_PUBLIC_API_URL=https://api.commitment-os.com
```

---

*End of document — feed into VS Code + Claude for implementation*
