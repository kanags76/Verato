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
PHASE 1 — LOCAL BACKEND (Weeks 1–7)
────────────────────────────────────────
Django REST API running on localhost:8000
All APIs tested via Swagger UI — no frontend written yet
Celery workers running locally for async tasks
Postgres 18 + Redis via Homebrew (native ARM64, no Docker)
310 tests passing — complete

PHASE 2 — CLOUD BACKEND (After Week 6.5)
──────────────────────────────────────────
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
│   └── analytics/
├── extraction/
│   ├── extractor.py
│   ├── prompt_builder.py
│   ├── parser.py
│   └── tests/fixtures/
└── manage.py
```

---

### Step 1.9 — Environment Variables ✓ DONE

All fields in `backend/.env`. Key additions beyond the basics:

```bash
# ── VERTEX AI (ADC auth — no API key) ────────────────────────────
GOOGLE_CLOUD_PROJECT=verato
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_EXTRACTION_MODEL=gemini-2.5-flash-lite
GEMINI_CLASSIFY_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=text-embedding-004

# ── WEEK 6 — Slack + SendGrid ─────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-placeholder          # global fallback
SLACK_SIGNING_SECRET=placeholder
SENDGRID_API_KEY=placeholder
DEFAULT_FROM_EMAIL=noreply@verato.app

# ── WEEK 6.5 — Slack OAuth + Invite emails ────────────────────────
SLACK_CLIENT_ID=placeholder
SLACK_CLIENT_SECRET=placeholder
SLACK_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/slack/oauth/callback/
APP_BASE_URL=http://localhost:3000            # frontend URL in invite emails

# ── PHASE 2 ──────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=placeholder
AWS_SECRET_ACCESS_KEY=placeholder
AWS_S3_BUCKET_NAME=verato-dev
```

---

### Step 1.10 — Django Settings ✓ DONE

Celery Beat schedule (as configured in `config/celery.py`):

```python
app.conf.beat_schedule = {
    'recompute-risk-scores': {
        'task':     'apps.commitments.tasks.recompute_risk_scores',
        'schedule': crontab(minute=0, hour='*/24'),   # daily
    },
    'send-deadline-nudges': {
        'task':     'apps.notifications.tasks.send_deadline_nudges',
        'schedule': crontab(minute=0, hour=9),         # 09:00 UTC daily
    },
    'send-weekly-digest': {
        'task':     'apps.notifications.tasks.send_weekly_digest',
        'schedule': crontab(minute=0, hour=7, day_of_week='monday'),
    },
}
```

---

## Part 2 — Daily Dev Workflow

```bash
# ── Start of session ─────────────────────────────────────
brew services list | grep -E "postgresql|redis"
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# ── Git flow ─────────────────────────────────────────────
git checkout develop && git pull origin develop
git checkout -b feature/weekN-description
# ... work ...
git add . && git commit -m "feat(area): what you did"
git push origin feature/weekN-description
# → GitHub: open PR → merge to develop
```

---

## Part 3 — MVP Build Plan

> All Phase 1 work is backend only.
> Swagger UI at `localhost:8000/api/schema/ui/` is your test interface.
> No frontend code is written until Phase 3.
> Analytics, conflict detection, and embeddings are Phase 2 — not built here.

---

### Week 1 — Extraction Engine ✓ DONE

Extraction engine, parser, prompt builder, and test fixtures complete. Explicit commitments extracted reliably from transcripts and import documents.

---

### Week 2 — Django Models + API Skeleton ✓ DONE

MVP tables in DB, serializers, CRUD ViewSets, persons endpoint, and Swagger UI all verified working.

---

### Week 3 — Ingestion Pipeline + Prior Import ✓ DONE

Transcript upload and prior import pipelines working end to end. Commitments saved as PENDING_REVIEW via Celery. Polling endpoint working.

---

### Week 3.5 — Knowledge Graph Foundation ✓ DONE

New models: `MeetingTopic`, `CommitmentTag`, `Commitment.tags` M2M, `Meeting.meeting_type`, `Meeting.summary`, `Person.first_seen_at`, `Person.meeting_count`.

Person profile gains timeline and topics endpoints. Commitment list gains `?tag=` filter. All new fields populated by the extraction pipeline Celery task.

---

### Week 4 — Commitment Actions + Dashboard API ✓ DONE

All CoS action endpoints built and tested. Dashboard returns correct counts.

Endpoints: `confirm`, `reject`, `escalate`, `resolve` actions on commitments. `GET /dashboard/` → `{overdue, at_risk, on_track, total_active}`.

---

### Week 5 — Risk Scoring + Status Automation ✓ DONE

`compute_risk_score()` formula: deadline proximity (50%) + owner delivery rate (35%) + update recency (15%).

`score_to_status()`: overdue → always escalated; ≥0.90 → escalated; ≥0.70 → at_risk; recovering → active.

`recompute_risk_scores()` Celery task runs daily (changed from 6h to 24h). Auto-creates `EscalationEvent(AUTO)` only on first auto-escalation (not if already escalated).

---

### Week 6 — Slack Nudges + Weekly Digest Email ✓ DONE

**Slack nudges:**
- `send_deadline_nudges()` task: 48h window, 20h cooldown (tracked by `NudgeLog`)
- Block Kit message with Done / Delayed / Blocked buttons
- `slack_actions` webhook: `_verify_slack_signature` → routes button clicks to status transitions
- `notify_cos_escalation()`: DM to CoS when commitment auto-escalates

**Weekly digest:**
- `send_weekly_digest()`: every Monday 07:00 UTC, per org
- Gemini Flash generates 2-3 sentence opening paragraph
- HTML template: `templates/emails/weekly_digest.html` — three sections: Overdue / At Risk / On Track
- Sent via SendGrid (django-anymail)

**Tests:** 24 notification tests + 8 Slack action tests.

---

### Week 6.5 — Self-Serve Sign-Up + Team Invites + Slack OAuth ✓ DONE

**Goal:** Organisations can sign up independently. Team admins can invite colleagues. Each org connects its own Slack workspace.

**Data model additions:**
- `Organisation.plan` — `individual` or `team`
- `User.is_org_admin` — gates invite-sending
- `Invitation` — 7-day expiring token, `create_for()`, `is_valid` property

**New endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register/` | POST | Create org + admin user + person in one atomic transaction → JWT |
| `/api/v1/auth/invite/` | POST | Admin sends email invite (re-invite refreshes token) |
| `/api/v1/auth/invite/validate/` | GET | `?token=` — public; returns email + org name (410 if expired/used) |
| `/api/v1/auth/invite/accept/` | POST | Validate token, create user + person, mark invite used → JWT |
| `/api/v1/persons/{id}/link-slack/` | POST | Set `slack_user_id` on person (own account, or admin for any) |
| `/api/v1/slack/oauth/start/` | GET | Redirect to Slack OAuth consent (org ID signed in state) |
| `/api/v1/slack/oauth/callback/` | GET | Exchange code → store per-org bot token in `org.settings` |

**Slack OAuth architecture:**
- Per-org bot token stored in `Organisation.settings['slack_token']`
- `_get_client(org=None)` tries org token first, falls back to global `SLACK_BOT_TOKEN`
- State parameter signed with `django.core.signing` (10-minute max age)

**Tests:** 29 new auth/invite/link-slack tests.

---

### Week 7 — API Gap-Fill (Frontend-Ready) ✓ DONE

**Goal:** Close all gaps between the built API and the user story requirements so the frontend can be built without needing further backend changes.

**New endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register/` | POST | Now returns `is_first_login: true` to drive first-run onboarding flow |
| `/api/v1/orgs/{id}/settings/` | PATCH | Admin-only; merge-updates `confidence_threshold`, `nudge_hours_before`, `digest_day`, `digest_hour` |
| `/api/v1/slack/status/` | GET | Returns `{connected, workspace_id, workspace_name}` for the Settings screen |
| `/api/v1/slack/test-message/` | POST | Sends a test DM to the requesting user's linked Slack account |
| `/api/v1/commitments/bulk-confirm/` | POST | Confirm all PENDING_REVIEW; accepts `{min_confidence}` to filter by confidence |
| `/api/v1/commitments/{id}/nudge/` | POST | Manually send a Slack deadline nudge to the owner right now |
| `/api/v1/tags/` | GET | Tag autocomplete ranked by org usage; `?q=` prefix filter |
| `PATCH /api/v1/commitments/{id}/` | — | Tags now writable — send `{tags: ["label1", "label2"]}`, normalised to lowercase, get_or_created per org |

**Priority field (added in Week 6.5):**
- `Commitment.priority` — `high` / `medium` (default) / `low`
- Filterable via `?priority=` on the list endpoint

**Tests:** 41 new tests. Total: 310 passing.

---

### Week 8 — API Hardening (Frontend Integration) ✓ DONE

**Goal:** Close gaps discovered during frontend integration; add audit trail, person management, and meeting participant management.

**New endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/logout/` | POST | Blacklist refresh token before clearing session → 204 |
| `/api/v1/commitments/{id}/reopen/` | POST | Reopen closed commitment (done/deferred/cancelled) → active |
| `/api/v1/commitments/{id}/history/` | GET | Unified audit log (CommitmentEvent + EscalationEvent), newest first |
| `/api/v1/persons/` | POST | Create a new person in the org |
| `/api/v1/persons/{id}/` | PATCH | Update person name, email, or role |
| `/api/v1/persons/merge/` | POST | Deduplicate persons; reassign all related records to primary |
| `/api/v1/meetings/{id}/` | PATCH | Update meeting title, date, meeting_type, or summary |
| `/api/v1/meetings/{id}/participants/` | GET | List meeting participants with confirmed flag |
| `/api/v1/meetings/{id}/add-participant/` | POST | Add person to meeting (existing or new) |
| `/api/v1/meetings/{id}/remove-participant/` | POST | Remove person from meeting → 204 |
| `/api/v1/meetings/{id}/link-participants/` | POST | Validate Gemini-detected participants |

**Model additions:**
- `CommitmentEvent` — append-only audit log; every action writes a row
- `MeetingParticipant.confirmed` — False = Gemini auto-linked, True = user-validated
- `Commitment.Status.DONE` — replaces `DELIVERED` (migration with RunPython backfill)
- `PATCH /commitments/{id}/` — now also writes `normalised_text` and logs `field_edited` events

**Extraction changes:**
- Gemini now returns `participants` array (names of everyone who spoke)
- Upload flow: Gemini runs immediately on upload (no gating); participants saved as `confirmed=False`
- User reviews commitments AND participants independently (no forced sequence)

---

### ✅ Phase 1 Backend Complete — All User Stories Covered

**All APIs for all 7 user story epics are now built.** The frontend can be built against Swagger UI at `localhost:8000/api/schema/ui/` without any further backend changes needed.

---

### Phase 2 — Frontend (Next.js) ← NEXT

Full plan: **`06_phase2_frontend_build_plan.md`**

Build the Next.js frontend by porting the working HTML prototype (`Design/Verato/Verato.html`) to production code. All 9 screens are already designed and responsive.

**Stack:** Next.js 14 (App Router) · TypeScript · Tailwind CSS · React Query · React Hook Form + Zod · Playwright E2E

**7 weeks:**
1. Foundation — project setup, design system, auth, shared components
2. Sign-up + onboarding (plan picker → Slack → import)
3. Dashboard (stat cards, status tabs, priority/tag filters, commitment rows)
4. Commitment detail (meta grid, actions, tags, audit trail)
5. Upload + extraction review (upload form, review queue, bulk-confirm, swipe-mobile)
6. People, Meetings list, Settings (org, Slack, team/invites)
7. Mobile polish, error states, Playwright E2E, deploy to Vercel

**Backend changes needed (3 small additions before Week 1):**
- `GET /api/v1/auth/invitations/` — list org pending invites
- `meeting` filter param on `POST /commitments/bulk-confirm/`
- `commitment_count` + `pending_count` on MeetingSerializer

**Design reference:** `Design/Verato/` — dark theme, JetBrains Mono, single 768px breakpoint

---

### Phase 3 — AWS Deployment (after frontend is stable)

```
□ Create RDS PostgreSQL 18
□ Create ElastiCache Redis (cache.t4g.micro)
□ Create S3 bucket for transcripts (verato-transcripts-prod)
□ Create ECR repository for Docker images
□ Create ECS cluster (verato)
□ Write Dockerfile for Django
□ Build + push Docker image to ECR
□ Create ECS task definitions: api / celery-worker / celery-beat
□ Create Application Load Balancer → HTTPS → ECS API
□ Store secrets in AWS Secrets Manager
□ Run Django migrations via ECS run-task
□ Verify: https://api.verato.app/api/health/ → 200
□ Verify: https://api.verato.app/api/schema/ui/ → Swagger UI
```

---

### Phase 4 — Intelligence Layer (after AWS deployment + 3 paying design partners)

| Feature | Branch |
|---|---|
| Analytics endpoints — delivery rates, risk summary, commitment volume | `feature/analytics` |
| Conflict detection — pgvector embeddings + Gemini Flash classification | `feature/conflicts` |
| Person knowledge graph — graph API endpoint + frontend rendering | `feature/person-graph` |
| Org calibration — recompile from ExtractionFeedback signals weekly | `feature/calibration` |
| Teams + Google Meet connectors | `feature/connectors` |

**Screens to generate (in order):**
1. Sign-up (register / invite / accept-invite)
2. Dashboard / command centre
3. Commitment detail
4. Upload & extraction review
5. Prior commitments import
6. Person profile — timeline view (MVP) + graph view (Phase 2)
7. Settings (Slack OAuth connection, Zoom webhook, org preferences)

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
AUTH (public — no JWT required)
  POST   /auth/register/            Create org + admin user + person → JWT + is_first_login: true
  POST   /auth/invite/accept/       Accept invite token → create account → JWT
  GET    /auth/invite/validate/     ?token= → {email, org_name}
  POST   /auth/token/               Login with email + password → JWT tokens
  POST   /auth/token/refresh/       Refresh expired access token

AUTH (requires JWT)
  POST   /auth/logout/              Blacklist refresh token then clear session → 204
  POST   /auth/invite/              Admin sends invite email
  GET    /auth/invitations/         List all sent invitations with status (admin only)

ORG
  PATCH  /orgs/{id}/settings/       Update confidence_threshold, nudge_hours_before, digest_day, digest_hour

DASHBOARD
  GET    /dashboard/                {overdue, at_risk, on_track, total_active}

MEETINGS
  POST   /meetings/upload/              Upload transcript (async → 202); Gemini extracts commitments + participants
  GET    /meetings/{id}/status/         Poll processing status; returns participant_count + confirmed_count
  GET    /meetings/{id}/                Detail — meeting_type, summary, topics[]
  PATCH  /meetings/{id}/                Update title, occurred_at, meeting_type, or summary
  GET    /meetings/                     List all org meetings
  POST   /meetings/import/              Upload prior commitments document (async → 202)
  GET    /meetings/{id}/participants/   List participants with confirmed flag + speaker_label
  POST   /meetings/{id}/add-participant/     Add person to meeting ({person_id} or {person: {}})
  POST   /meetings/{id}/remove-participant/  Remove person from meeting ({person_id}) → 204
  POST   /meetings/{id}/link-participants/   Validate Gemini-detected participants (link/create/skip)
  POST   /meetings/zoom/webhook/        Zoom webhook receiver (stretch)

COMMITMENTS
  GET    /commitments/              List with filters:
                                    ?status= ?owner= ?priority= ?deadline_before= ?risk_gte=
                                    ?source= ?tags__label= ?meeting=
  GET    /commitments/{id}/         Detail + escalations[] + tags[]
  PATCH  /commitments/{id}/         Update normalised_text, owner, deadline, priority, tags
                                    All changes logged to CommitmentEvent (field_edited)
  POST   /commitments/bulk-confirm/    Confirm all PENDING_REVIEW; optional {min_confidence, meeting}
  POST   /commitments/{id}/confirm/    PENDING_REVIEW → ACTIVE; logs CommitmentEvent(confirmed)
  POST   /commitments/{id}/reject/     → CANCELLED + log feedback signal; logs CommitmentEvent(rejected)
  POST   /commitments/{id}/escalate/   → ESCALATED + EscalationEvent; logs CommitmentEvent(escalated)
  POST   /commitments/{id}/resolve/    {outcome: done|deferred|cancelled, note?, new_deadline?}
                                       logs CommitmentEvent(resolved)
  POST   /commitments/{id}/reopen/     Reopen done/deferred/cancelled → active; logs CommitmentEvent(reopened)
  POST   /commitments/{id}/nudge/      Send Slack deadline DM to owner now; logs CommitmentEvent(nudged)
  GET    /commitments/{id}/history/    Unified audit log — CommitmentEvent + EscalationEvent, newest first

TAGS
  GET    /tags/                     Tag autocomplete; ?q= prefix filter; ranked by usage

PERSONS
  GET    /persons/                  List org participants
  POST   /persons/                  Create a new person {name, email?, role?}
  GET    /persons/{id}/             Person detail + delivery rate + lineage
  PATCH  /persons/{id}/             Update name, email, or role
  GET    /persons/{id}/timeline/    Chronological meetings + commitments
  GET    /persons/{id}/topics/      Tag frequency list
  POST   /persons/{id}/link-slack/  Set slack_user_id
  POST   /persons/merge/            Deduplicate: {primary_id, duplicate_ids[]}
                                    Reassigns commitments, escalations, events, meeting participants to primary

SLACK
  GET    /slack/status/             {connected, workspace_id, workspace_name}
  POST   /slack/test-message/       Send test DM to requesting user's Slack
  POST   /slack/actions/            Slack interactive button handler
  GET    /slack/oauth/start/        Redirect to Slack OAuth (authenticated only)
  GET    /slack/oauth/callback/     OAuth callback — save per-org token
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
pytest apps/accounts/tests/test_auth.py -v
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

### Credentials reference

| Week | Credential | Where to get it |
|---|---|---|
| Now | Vertex AI ADC | `gcloud auth application-default login` |
| Week 6 | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | https://api.slack.com/apps |
| Week 6 | `SENDGRID_API_KEY` | https://app.sendgrid.com/settings/api_keys |
| Week 6.5 | `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` | Same Slack app — OAuth & Permissions tab |
| Week 6 (stretch) | `ZOOM_*` keys | https://marketplace.zoom.us/develop/create |
| Phase 2 | AWS credentials | https://console.aws.amazon.com |
| Phase 3 | GCP credentials | https://console.cloud.google.com |

---

*Backend-first: all APIs built and tested. Phase 1 complete — 310 tests passing.
Next step: build the Next.js frontend using the design files in Design/Verato/.*
