# Verato — Build Plan
## Apple Silicon Mac · GitHub · Localhost First · AWS then GCP

> **Machine:** Apple Silicon Mac (M1/M2/M3)
> **Source control:** GitHub (private) — https://github.com/kanags76/Verato
> **Local dev:** Django + Celery run natively in venv · Postgres + Redis via Homebrew (no Docker)
> **API testing:** Swagger UI at localhost:8000/api/schema/ui/ (no frontend needed)
> **Deployment sequence:** Backend → AWS ECS first · Frontend → GCP Cloud Run second
> **Frontend build tool:** Google AI Studio (generates Next.js, deployed to Cloud Run)

---

## EVERY SESSION — Run these at the start of each coding session

```bash
# 1. Verify services are up
brew services list | grep -E "postgresql|redis"
pg_isready        # → localhost:5432 - accepting connections
redis-cli ping    # → PONG

# 2. If either is stopped, restart it
brew services start postgresql@18
brew services start redis

# 3. Navigate to project + activate venv
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# 4. Open four terminal tabs in VS Code:

# Tab 1 — Django API server
python manage.py runserver
# → http://localhost:8000
# → Swagger UI: http://localhost:8000/api/schema/ui/

# Tab 2 — Celery worker (only when testing async tasks)
celery -A config worker --loglevel=info

# Tab 3 — Tests
pytest -v --tb=short

# Tab 4 — Git / migrations / shell (free tab)
```

### End of session
```bash
# Stop Django   → Ctrl+C in Tab 1
# Stop Celery   → Ctrl+C in Tab 2
# Services stay running (lightweight) — or stop them:
brew services stop postgresql@18
brew services stop redis
```

---

## ONE-TIME SETUP STATUS

| Step | Description | Status |
|---|---|---|
| 1.1 | GitHub repo created | ✓ DONE — kanags76/Verato (private) |
| 1.2 | GitHub auth | ✓ DONE — gh CLI authenticated |
| 1.3 | Project directory + git | ✓ DONE — ~/Documents/Programs/Verato/backend |
| 1.4 | Branch strategy | ⏳ TODO |
| 1.5 | Prerequisites (PG18, Redis, Python venv) | ✓ DONE — Homebrew, no Docker |
| 1.6 | VS Code setup | ⏳ TODO |
| 1.7 | Docker Compose | N/A — using Homebrew instead |
| 1.8 | Django project scaffold | ✓ DONE — manage.py, 5 apps, extraction module |
| 1.9 | Environment variables (.env) | ✓ DONE — all fields populated |
| 1.10 | Django settings (base/local/production) | ✓ DONE |
| 1.11 | URLs, Swagger, Celery config | ✓ DONE — verified working |
| 1.12 | DRF Spectacular config | ✓ DONE — Swagger UI live at /api/schema/ui/ |
| 1.13 | First migration + superuser | ✓ DONE — admin/admin1234 |
| 1.14 | Gemini API verification | ⏳ TODO — add GEMINI_API_KEY to .env |
| 1.15 | GitHub Actions CI | ⏳ TODO |

---

## The Three Phases — What You're Building and When

```
PHASE 1 — LOCAL BACKEND (Weeks 1–6)
────────────────────────────────────
Django REST API running on localhost:8000
All APIs tested via Swagger UI — no frontend written yet
Celery workers running locally for async tasks
Postgres 18 + Redis via Homebrew (native ARM64, no Docker)

PHASE 2 — CLOUD BACKEND (After Week 6)
────────────────────────────────────────
Push Django backend to AWS ECS
Postgres moves to RDS, Redis to ElastiCache
Swagger UI still works — now at api.verato.app/api/schema/ui/
APIs fully operational in the cloud before frontend exists

PHASE 3 — FRONTEND (After backend is stable on AWS)
─────────────────────────────────────────────────────
Use Google AI Studio to generate Next.js frontend
Frontend calls the AWS API over HTTPS
Deploy Next.js to GCP Cloud Run
```

---

## On Swagger UI — Your Development Dashboard

Swagger UI is your testing interface for the entire backend development phase.
You do not need a frontend to develop, test, or demonstrate the API.

```
http://localhost:8000/api/schema/ui/
```

**The workflow for every new endpoint:**
```
1. Write Django view + serializer
2. Open Swagger UI
3. Click the endpoint → Try it out → Execute
4. Verify response matches spec
5. Write pytest test to lock in the behaviour
6. Move to next endpoint
```

---

## Part 1 — One-Time Setup

### Step 1.1–1.5 ✓ DONE

Repo, auth, directory, prerequisites all complete. See `01_local_dev_mac_setup.md` for service management reference.

---

### Step 1.6 — VS Code Setup ⏳ TODO

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.black-formatter
code --install-extension batisteo.vscode-django
code --install-extension humao.rest-client
code --install-extension eamodio.gitlens
code --install-extension github.vscode-pull-request-github
```

Create `.vscode/settings.json` in `~/Documents/Programs/Verato/`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  },
  "git.autofetch": true,
  "terminal.integrated.env.osx": {
    "DJANGO_SETTINGS_MODULE": "config.settings.local"
  }
}
```

---

### Step 1.7 — Branch Strategy ⏳ TODO

```bash
cd ~/Documents/Programs/Verato
git checkout -b develop
git push origin develop
# In GitHub: Settings → Branches → set develop as default branch
```

```
main         production. Protected. Merge from develop only.
develop      integration. All feature branches merge here.
feature/*    one per week, e.g. feature/week1-extraction-engine
fix/*        bug fixes, e.g. fix/risk-score-null-owner
```

---

### Step 1.8 — Django Project Scaffold ✓ DONE

```
~/Documents/Programs/Verato/backend/
├── config/
│   └── settings/
│       ├── base.py
│       ├── local.py
│       └── production.py
├── apps/
│   ├── accounts/
│   ├── meetings/
│   ├── commitments/
│   ├── notifications/
│   └── analytics/        ← kept for Phase 2; empty for now
├── extraction/
│   ├── extractor.py
│   ├── prompt_builder.py
│   ├── parser.py
│   └── tests/fixtures/
└── manage.py
```

---

### Step 1.9 — Environment Variables ✓ DONE (base) / ⏳ Add remaining fields

Current `.env` has DB + Redis. Add these fields now:

```bash
# Add to backend/.env:
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=replace-with-50-random-chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── WEEK 1 — get this now ─────────────────────────────────
# https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_EXTRACTION_MODEL=gemini-1.5-pro
GEMINI_DIGEST_MODEL=gemini-1.5-flash

# ── WEEK 6 ───────────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-placeholder
SLACK_SIGNING_SECRET=placeholder
SENDGRID_API_KEY=placeholder
DEFAULT_FROM_EMAIL=noreply@verato.app

# ── PHASE 1 STRETCH — Zoom (add when ready) ──────────────
ZOOM_CLIENT_ID=placeholder
ZOOM_CLIENT_SECRET=placeholder
ZOOM_WEBHOOK_SECRET_TOKEN=placeholder

# ── PHASE 2 ──────────────────────────────────────────────
AWS_ACCESS_KEY_ID=placeholder
AWS_SECRET_ACCESS_KEY=placeholder
AWS_S3_BUCKET_NAME=verato-dev
AWS_S3_REGION=us-east-1
```

Note: `GEMINI_EMBEDDING_MODEL` removed — no embeddings in MVP.

---

### Step 1.10 — Django Settings ✓ DONE

Key change from original: remove `GEMINI_EMBEDDING_MODEL` from base.py settings.
Remove `conflicts` and `analytics` from SPECTACULAR_SETTINGS TAGS (not built in MVP).

Updated `SPECTACULAR_SETTINGS` tags:

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'Verato API',
    'DESCRIPTION': '''
## Verato — Backend API

Extracts commitments from meeting transcripts, tracks them, scores risk, nudges owners.

### Authentication
All endpoints (except /api/v1/auth/token/) require a JWT Bearer token.
1. Call POST /api/v1/auth/token/ with username + password
2. Copy the access token
3. Click Authorize → enter: Bearer <token>
    ''',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'filter': True,
        'docExpansion': 'list',
    },
    'TAGS': [
        {'name': 'auth',        'description': 'Authentication — JWT tokens'},
        {'name': 'dashboard',   'description': 'Summary stats for CoS command centre'},
        {'name': 'meetings',    'description': 'Upload transcripts, import prior commitments, receive webhooks'},
        {'name': 'commitments', 'description': 'Confirm, escalate, resolve, defer, list with filters'},
        {'name': 'persons',     'description': 'Org participants, used for owner picker'},
    ],
}
```

---

### Step 1.11 — URLs, Swagger, Celery ✓ DONE

Celery Beat schedule updated to match MVP (no analytics, no conflict recompilation):

```python
# config/celery.py
app.conf.beat_schedule = {
    'recompute-risk-scores': {
        'task':     'apps.commitments.tasks.recompute_risk_scores',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'send-deadline-nudges': {
        'task':     'apps.notifications.tasks.send_deadline_nudges',
        'schedule': crontab(minute=0, hour=9),
    },
    'send-weekly-digest': {
        'task':     'apps.notifications.tasks.send_weekly_digest',
        'schedule': crontab(minute=0, hour=7, day_of_week='monday'),
    },
}
```

Remove from original: `recompile-org-calibrations` beat task — Phase 2 only.

---

### Step 1.14 — Gemini API Verification ⏳ TODO

Set `GEMINI_API_KEY` in `.env` first (https://aistudio.google.com/app/apikey), then:

```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate

python << 'PYEOF'
from decouple import config
import google.generativeai as genai

key = config('GEMINI_API_KEY')
genai.configure(api_key=key)

print("1. Testing Gemini Pro (extraction model)...")
pro = genai.GenerativeModel("gemini-1.5-pro")
r = pro.generate_content('Return JSON only: [{"test": "ok"}]')
print(f"   Response: {r.text.strip()}")

print("2. Testing Gemini Flash (digest model)...")
flash = genai.GenerativeModel("gemini-1.5-flash")
r = flash.generate_content('Summarise in one sentence: Sarah is overdue on the pricing deck.')
print(f"   Response: {r.text.strip()}")

print("\nGemini working — start Week 1")
PYEOF
```

Note: No embedding test needed — embeddings are Phase 2.

---

### Step 1.15 — GitHub Actions CI ⏳ TODO

```bash
mkdir -p ~/Documents/Programs/Verato/.github/workflows

cat > ~/Documents/Programs/Verato/.github/workflows/backend-ci.yml << 'EOF'
name: Backend CI

on:
  push:
    branches: [develop, main]
    paths: ['backend/**']
  pull_request:
    branches: [develop]
    paths: ['backend/**']

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: verato_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements.txt

      - name: Run tests
        working-directory: backend
        env:
          DJANGO_SETTINGS_MODULE: config.settings.local
          DJANGO_SECRET_KEY: ci-secret-not-real
          DB_NAME: verato_test
          DB_USER: postgres
          DB_PASSWORD: postgres
          DB_HOST: localhost
          REDIS_URL: redis://localhost:6379/0
          GEMINI_API_KEY: placeholder
        run: pytest --cov=apps --cov=extraction -v
EOF
```

Note: No pgvector in CI — not needed for MVP. Plain postgres:18 image.

---

## Part 2 — Daily Dev Workflow

```bash
# ── Start of session ─────────────────────────────────────
brew services list | grep -E "postgresql|redis"
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# ── Four VS Code terminal tabs ───────────────────────────
# Tab 1 — Django API
python manage.py runserver

# Tab 2 — Celery worker (only when testing async tasks)
celery -A config worker --loglevel=info

# Tab 3 — Tests
pytest -v --tb=short

# Tab 4 — Git / general commands

# ── Git flow ─────────────────────────────────────────────
git checkout develop && git pull origin develop
git checkout -b feature/weekN-description
# ... work ...
git add . && git commit -m "feat(area): what you did"
git push origin feature/weekN-description
# → GitHub: open PR → merge to develop
```

---

## Part 3 — 6-Week MVP Build Plan

> All work in Phase 1 is backend only.
> Swagger UI at `localhost:8000/api/schema/ui/` is your test interface.
> No frontend code is written until Phase 3.
> Analytics, conflict detection, and embeddings are Phase 2 — not built here.

---

### Week 1 — Extraction Engine
**Branch:** `feature/week1-extraction-engine`
**Goal:** Python function that takes transcript text and returns structured commitment JSON. Also a separate import extraction function for prior commitment documents.

**Tasks:**
- [ ] `extraction/extractor.py` — `extract_commitments(meeting, transcript, participants)`
- [ ] `extraction/importer.py` — `extract_from_document(text)` — different prompt, no participant list, looks for list/table structure
- [ ] `extraction/parser.py` — `safe_json_parse()` handles Gemini markdown fences
- [ ] `extraction/prompt_builder.py` — `build_transcript_prompt()` and `build_import_prompt()`
- [ ] Create 5 test transcripts in `extraction/tests/fixtures/`
- [ ] Create 3 test import documents in `extraction/tests/fixtures/` (Notion export, spreadsheet paste, plain text list)
- [ ] `extraction/tests/test_extractor.py` — test each transcript fixture, assert precision > 85%
- [ ] `extraction/tests/test_importer.py` — test each import fixture, assert owner + deadline extraction

```bash
pytest extraction/tests/ -v
```

**Done when:** `pytest extraction/tests/` passes. Explicit commits extracted reliably from transcripts. Structured items extracted reliably from document pastes.

**What's NOT here:** No `conflict_detector.py`, no embeddings, no calibration. Those are Phase 2.

---

### Week 2 — Django Models + API Skeleton
**Branch:** `feature/week2-models-api`
**Goal:** MVP tables in DB. Basic CRUD endpoints visible in Swagger UI.

**Tasks:**
- [ ] `apps/accounts/models.py` — Organisation, User, Person (see data model)
- [ ] `apps/meetings/models.py` — Meeting, MeetingParticipant
- [ ] `apps/commitments/models.py` — Commitment (MVP fields only), EscalationEvent, ExtractionFeedback
- [ ] All migrations — no pgvector, no RunSQL needed
- [ ] Serializers for all models
- [ ] ViewSets — CRUD for commitments and meetings
- [ ] `GET /api/v1/persons/` — list org participants
- [ ] URL files for each app; wire into `config/urls.py`
- [ ] Open Swagger UI → verify all endpoints appear → test GET/POST

**Key Swagger test:**
```
POST /api/v1/auth/token/ → get JWT → Authorize
GET  /api/v1/commitments/ → empty list, 200 OK
POST /api/v1/commitments/ → create test commitment
GET  /api/v1/commitments/{id}/ → retrieve it
GET  /api/v1/persons/ → empty list, 200 OK
```

**Done when:** All migrations apply cleanly. CRUD works in Swagger with no errors.

**What's NOT here:** No Conflict model, no OrgCalibration model, no embedding field on Commitment.

---

### Week 3 — Ingestion Pipeline + Prior Import
**Branch:** `feature/week3-ingestion`
**Goal:** Upload transcript via Swagger → Celery processes → commitments appear in DB. Import document → structured commitments appear for review.

**Tasks:**

*Transcript ingestion:*
- [ ] `POST /api/v1/meetings/upload/` — accepts transcript text or file (.txt, .vtt, .srt, .docx)
- [ ] `apps/meetings/tasks.py` — `process_meeting` Celery task — calls `extract_commitments()`, saves results as PENDING_REVIEW
- [ ] `GET /api/v1/meetings/{id}/status/` — polling endpoint (pending / processing / complete / failed)
- [ ] Wire extraction module into Celery task

*Prior commitments import:*
- [ ] `POST /api/v1/meetings/import/` — accepts document text or file (.csv, .xlsx, .docx, .txt, .md)
- [ ] `apps/meetings/tasks.py` — `process_import` Celery task — calls `extract_from_document()`, saves results as PENDING_REVIEW with `source='import'`
- [ ] `GET /api/v1/meetings/import/{id}/status/` — polling endpoint

**Swagger test flow:**
```
# Transcript flow
POST /api/v1/meetings/upload/           → 202 + meeting_id
GET  /api/v1/meetings/{id}/status/      → poll until "complete"
GET  /api/v1/commitments/?meeting={id}  → extracted PENDING_REVIEW commitments

# Import flow
POST /api/v1/meetings/import/           → 202 + import_id
GET  /api/v1/meetings/import/{id}/status/ → poll until "complete"
GET  /api/v1/commitments/?source=import   → extracted PENDING_REVIEW commitments
```

**Done when:** Both upload and import pipelines work end to end via Swagger. Commitments appear in DB as PENDING_REVIEW.

---

### Week 4 — Commitment Actions + Dashboard API
**Branch:** `feature/week4-commitment-actions`
**Goal:** All CoS action endpoints built and tested in Swagger. Dashboard endpoint returns correct data.

**Tasks:**
- [ ] `POST /api/v1/commitments/{id}/confirm/` — PENDING_REVIEW → ACTIVE; logs ExtractionFeedback (confirmed)
- [ ] `POST /api/v1/commitments/{id}/reject/` — discards commitment; logs ExtractionFeedback (rejected)
- [ ] `POST /api/v1/commitments/{id}/escalate/` — status → ESCALATED; creates EscalationEvent
- [ ] `POST /api/v1/commitments/{id}/resolve/` — body: `{outcome: delivered|deferred|cancelled, note, new_deadline?}`
- [ ] `PATCH /api/v1/commitments/{id}/` — update owner, deadline; triggers risk score recompute
- [ ] `GET /api/v1/dashboard/` — returns: `{overdue, at_risk, on_track, total_active}`
- [ ] Commitment list filters: `?status=`, `?owner=`, `?deadline_before=`, `?risk_gte=`, `?source=`
- [ ] `GET /api/v1/commitments/{id}/` — detail with full history log

**Swagger test:**
```
POST /api/v1/commitments/{id}/confirm/  → status: active
POST /api/v1/commitments/{id}/escalate/ → status: escalated
POST /api/v1/commitments/{id}/resolve/  → {outcome: "delivered"} → status: delivered
GET  /api/v1/dashboard/                 → {overdue: 1, at_risk: 2, on_track: 5, total_active: 8}
GET  /api/v1/commitments/?status=at_risk → filtered list
```

**Done when:** Every endpoint the frontend will ever call is functional in Swagger with correct status transitions.

---

### Week 5 — Risk Scoring + Status Automation
**Branch:** `feature/week5-risk-scoring`
**Goal:** Commitments change status automatically. Risk scores always fresh. CoS notified on escalation.

**Tasks:**
- [ ] `apps/commitments/risk.py` — `compute_risk_score(commitment)` → float 0.0–1.0
  - Deadline proximity: 40%
  - Owner delivery rate: 30%
  - Recency of updates: 10%
  - (dependency health component removed — no dependency tracking in MVP; weight redistributed)
- [ ] `apps/commitments/tasks.py` — `recompute_risk_scores()` Celery task — runs over all ACTIVE + AT_RISK commitments
- [ ] `apps/commitments/tasks.py` — `score_to_status()` — auto-transitions ACTIVE→AT_RISK→ESCALATED
- [ ] Celery Beat schedule — every 6 hours
- [ ] `apps/notifications/tasks.py` — `notify_cos_escalation()` — Slack DM to CoS when commitment auto-escalates

**Risk score formula (MVP — no dependencies):**
```python
# Component weights adjusted for MVP (no dependency tracking)
score += time_score   * 0.50   # deadline proximity (up from 40%)
score += owner_risk   * 0.35   # owner delivery rate (up from 30%)
score += recency_risk * 0.15   # update recency (up from 10%)
```

**Done when:** Create a commitment with a past deadline → Celery run → status auto-escalates to ESCALATED. Commitments due in 2 days → AT_RISK.

---

### Week 6 — Slack Nudges + Weekly Digest Email
**Branch:** `feature/week6-notifications`
**Pre-req:** Create Slack app at https://api.slack.com/apps; set `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SENDGRID_API_KEY` in `.env`

**Tasks:**

*Slack nudges:*
- [ ] `apps/notifications/slack.py` — Slack Bolt app setup
- [ ] `apps/notifications/tasks.py` — `send_deadline_nudges()` — DM to owner 48hr before deadline
  - Message includes: commitment text, original quote, deadline, three buttons
- [ ] Slack action handler — owner presses Done → DELIVERED; Delayed → asks for date → DEFERRED; Blocked → asks for reason → AT_RISK + CoS notified
- [ ] No-reply handler — 24hr after nudge with no response → CoS notified

*Weekly digest email:*
- [ ] Configure django-anymail with SendGrid
- [ ] `apps/notifications/tasks.py` — `send_weekly_digest()` — Monday 07:00 UTC
  - Calls Gemini Flash to generate 2–3 sentence opening paragraph
  - Three sections: Overdue / At Risk / On Track
- [ ] HTML email template — `templates/emails/weekly_digest.html`

*Zoom webhook (stretch — complete if time allows):*
- [ ] `apps/meetings/connectors/zoom.py` — webhook handler for `meeting.transcript_completed`
- [ ] Queues `process_meeting` Celery task with auto-ingested transcript

**Done when (minimum):** Owner receives Slack DM. Presses Done. Dashboard shows DELIVERED. Monday digest email arrives with correct sections and AI-generated intro paragraph.

**Done when (stretch):** End a Zoom meeting → transcript auto-ingested → commitments extracted without manual upload.

---

### ✅ MVP Backend Complete — Phase 2: Deploy to AWS

**AWS deployment checklist:**
```
□ Create RDS PostgreSQL 18
□ Create ElastiCache Redis (cache.t4g.micro)
□ Create S3 bucket for transcripts (verato-transcripts-prod)
□ Create ECR repository for Docker images
□ Create ECS cluster (verato)
□ Write Dockerfile for Django (see mac_setup.md Phase 2 section)
□ Build + push Docker image to ECR
□ Create ECS task definitions: api / celery-worker / celery-beat
□ Create Application Load Balancer → HTTPS → ECS API
□ Store secrets in AWS Secrets Manager
□ Run Django migrations via ECS run-task
□ Verify: https://api.verato.app/api/health/ → 200
□ Verify: https://api.verato.app/api/schema/ui/ → Swagger UI
```

Note: No pgvector setup needed in RDS for Phase 2 deployment. Add when conflict detection is built.

---

### Phase 2 — Intelligence Layer (after AWS deployment + 3 paying design partners)

| Week | Feature | Branch |
|---|---|---|
| 7 | Analytics endpoints — delivery rates, risk summary, commitment volume | `feature/week7-analytics` |
| 8 | Conflict detection — pgvector embeddings + Gemini Flash classification | `feature/week8-conflicts` |
| 9 | Org calibration — recompile from ExtractionFeedback signals weekly | `feature/week9-calibration` |
| 10 | Teams + Google Meet connectors | `feature/week10-connectors` |

---

### Phase 3 — Frontend on GCP (after Phase 2 is stable)

1. Open Google AI Studio (https://aistudio.google.com)
2. Generate Next.js frontend — describe each screen, paste endpoint details from Swagger
3. All API calls point to AWS ALB URL
4. Deploy to GCP Cloud Run

**Screens to generate (in order):**
1. Dashboard / command centre
2. Commitment detail
3. Upload & extraction review
4. Prior commitments import
5. Settings (Slack connection, Zoom webhook, org preferences)

---

## Part 4 — Reference

### URLs during local development

| URL | What it is |
|---|---|
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — main test interface** |
| `http://localhost:8000/api/schema/redoc/` | ReDoc — clean API docs |
| `http://localhost:8000/api/schema/` | Raw OpenAPI JSON |
| `http://localhost:8000/api/health/` | Health check |
| `http://localhost:8000/admin/` | Django admin |

### Full MVP API surface

```
AUTH
  POST   /auth/token/              Get JWT access + refresh tokens
  POST   /auth/token/refresh/      Refresh expired access token
  POST   /auth/token/blacklist/    Logout

DASHBOARD
  GET    /dashboard/               {overdue, at_risk, on_track, total_active}

MEETINGS
  POST   /meetings/upload/         Upload transcript text or file (async → 202)
  GET    /meetings/{id}/status/    Poll processing status
  GET    /meetings/                List all org meetings
  POST   /meetings/import/         Upload prior commitments document (async → 202)
  GET    /meetings/import/{id}/status/  Poll import status
  POST   /meetings/zoom/webhook/   Zoom webhook receiver (stretch Week 6)

COMMITMENTS
  GET    /commitments/             List with filters:
                                   ?status=pending_review|active|at_risk|escalated|delivered
                                   ?owner={person_id}
                                   ?deadline_before=YYYY-MM-DD
                                   ?risk_gte=0.7
                                   ?source=import|transcript
  GET    /commitments/{id}/        Detail + history log
  PATCH  /commitments/{id}/        Update owner, deadline
  POST   /commitments/{id}/confirm/    PENDING_REVIEW → ACTIVE
  POST   /commitments/{id}/reject/     Discard + log feedback signal
  POST   /commitments/{id}/escalate/   → ESCALATED + EscalationEvent
  POST   /commitments/{id}/resolve/    {outcome, note, new_deadline?}

PERSONS
  GET    /persons/                 List org participants (for owner picker)
  GET    /persons/{id}/            Person detail + delivery rate
```

### Key commands

```bash
# Migrations
python manage.py makemigrations [app_name]
python manage.py migrate

# Django shell
python manage.py shell

# Tests
pytest -v
pytest apps/commitments/ -v
pytest -k "test_risk" -v
pytest --cov=apps --cov=extraction --cov-report=html

# Services (Homebrew)
brew services start postgresql@18
brew services start redis
brew services list

# Port conflicts
lsof -i :8000   # Django
lsof -i :5432   # Postgres
lsof -i :6379   # Redis
```

### Credentials — fill in .env as you reach each week

| Week | Credential | Where to get it |
|---|---|---|
| Now | `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| Week 6 | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | https://api.slack.com/apps |
| Week 6 | `SENDGRID_API_KEY` | https://app.sendgrid.com/settings/api_keys |
| Week 6 (stretch) | `ZOOM_*` keys | https://marketplace.zoom.us/develop/create |
| Phase 2 | AWS credentials | https://console.aws.amazon.com |
| Phase 3 | GCP credentials | https://console.cloud.google.com |

---

*Backend-first: build and test everything in Swagger before touching the frontend.
MVP is 6 weeks. Analytics, conflict detection, and embeddings are Phase 2.*
