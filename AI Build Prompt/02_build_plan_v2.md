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
    'poll-gmail-replies': {
        'task':     'apps.notifications.tasks.poll_gmail_replies',
        'schedule': crontab(minute='*/15'),  # every 15 min — per-org interval enforced in task
    },
    'sync-calendar-events': {
        'task':     'apps.notifications.tasks.sync_calendar_events',
        'schedule': crontab(minute='*/15'),  # every 15 min — syncs Google Meet events for all connected orgs
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

### Week 9 — Production Hardening ✓ DONE

**Goal:** Fix production issues discovered during first live use of the deployed backend.

**Fixes and additions:**

| Area | Change |
|---|---|
| Slack OAuth | `?auth=<JWT>` query param always checked first — browser session cookies for wrong user were bypassing JWT |
| New endpoint | `GET /auth/me/` — returns current user profile + org (`{id, email, name, is_org_admin, organisation}`) |
| Upload | `occurred_at` now optional on `MeetingUploadSerializer` — defaults to `timezone.now()` if omitted |
| Upload | `request.FILES` explicitly merged into `request.data` — axios Content-Type boundary handling was losing files |
| Gemini | `GEMINI_API_KEY` now read via `config()` in `settings/base.py` — `getattr(settings, 'GEMINI_API_KEY', None)` was always returning `None` causing EC2 to fall back to ADC (which doesn't exist on EC2) |
| Admin | Django admin pipeline status dashboard at `/admin/meetings/meeting/pipeline-status/` — Redis queue depths, status counts, stuck meetings, recent failures, reprocess/mark-failed actions |
| Admin | `PipelineStatus` proxy model adds a sidebar link in the MEETINGS section |

**New endpoint:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/me/` | GET | Current user + org — used by frontend on every page load to confirm session and get org context |

---

### Week 11 — Slack User Management ✓ DONE

Search Slack workspace by email/name, import selected users as Persons, full workspace sync with email-match auto-linking and confirm flow.

| Endpoint | Description |
|---|---|
| `GET /slack/users/?q=` | Search by email or name |
| `POST /slack/users/import/` | Import selected users; link or create Person |
| `GET /slack/users/sync/` | Full workspace sync — matched/unmatched lists |
| `POST /slack/users/sync/` | Confirm matches `{confirmations: [{person_id, slack_user_id}]}` |

---

### Week 14 — Google Calendar + Google Meet Passive Ingestion ✓ DONE

**Goal:** Eliminate manual transcript upload for Google Meet meetings.

**Data model:** `CalendarConnection` (per-org OAuth) + `CalendarEvent` (per Meet event with status machine).

**Celery tasks:**
- `sync_calendar_events` — every 15 min: pulls Google Calendar API events with Meet links, `get_or_create` on `(org, google_event_id)`, schedules `fetch_google_meet_transcript` only for newly created events
- `fetch_google_meet_transcript(calendar_event_id)` — downloads transcript from Google Drive, creates Meeting, queues `process_meeting`

**Token refresh:** `_build_calendar_credentials(conn)` helper checks expiry, refreshes via `google.oauth2.credentials.Credentials`, saves updated token back to CalendarConnection.

**OAuth fix:** `OAUTHLIB_RELAX_TOKEN_SCOPE=1` set before `flow.fetch_token()` — required because Google appends `openid` to returned scopes.

**New endpoints:** `GET /calendar/status/` · `GET /calendar/oauth/start/` · `GET /calendar/oauth/callback/` · `POST /calendar/disconnect/`

**Admin:** `CalendarConnectionAdmin` (transcripts_detected badge), `CalendarEventAdmin` (colour-coded status, Drive file link, Meeting link).

**Notifications:** On processing complete, creates InAppNotification with type `meeting_ready` or `meeting_failed`.

---

### Week 14.5 — Gemini Auto-Title + Optional Meeting Title ✓ DONE

- `title` is now optional on both upload and import endpoints (blank string, no fallback)
- Gemini extraction prompt now returns `meeting_title` field — a concise 3–8 word summary of the meeting
- `process_meeting` and `process_import` tasks: if `meeting.title` is blank and Gemini returned a title, sets it automatically
- `parse_extraction_response` extracts `meeting_title` from Gemini JSON into `result["title"]`

---

### Week 15 — Zoom Passive Ingestion ✓ DONE

**Goal:** Auto-process Zoom cloud recordings the moment they're ready.

**Data model:** `ZoomConnection` (per-org OAuth) + `ZoomRecording` (per recording webhook event).

**Flow:**
1. Org connects Zoom via OAuth (`zoom_oauth_start` → user authorises → `zoom_oauth_callback` saves tokens)
2. Zoom sends `recording.completed` webhook to `POST /zoom/webhook/`
3. Webhook: HMAC-SHA256 signature verified (`v0:{timestamp}:{body}` with ZOOM_WEBHOOK_SECRET), finds org by `zoom_account_id`, creates `ZoomRecording`, queues `fetch_zoom_transcript`
4. `fetch_zoom_transcript`: downloads VTT from Zoom using `download_url?access_token={download_token}`, creates Meeting, queues `process_meeting`
5. `process_meeting` fires → Gemini extraction → InAppNotification created

**Zoom app type:** General App (user-managed OAuth). Required scope: `recording:read`. Webhook event: `recording.completed`.

**New endpoints:** `GET /zoom/status/` · `GET /zoom/oauth/start/` · `GET /zoom/oauth/callback/` · `POST /zoom/disconnect/` · `POST /zoom/webhook/`

**Admin:** `ZoomConnectionAdmin`, `ZoomRecordingAdmin` (colour-coded status, Meeting link).

---

### ✅ Phase 2.8 — Passive Ingestion Complete

Both Google Meet (via Calendar + Drive) and Zoom (via webhook + recording download) are live. Zero-click transcript processing is now operational.

---

### Week 16 — Frontend Complete ✓ DONE

All frontend screens built by Google AI Studio, committed to `frontend/`. Stack: React 19 + Vite + TypeScript + Tailwind v4 + React Query.

**Screens:** Dashboard · Commitment Detail · Meetings · Meeting Detail · People · Settings · Login · Register · Onboarding (Connect Slack, Import Tracker)

**Components:** UploadModal · ClarificationModal · ImportSuccessModal · LinkSlackPeopleModal · ManualSlackLinkModal · NotificationsModal · AppShell · Sidebar · TopBar

**Integrations wired in frontend:**
- Slack: connect/disconnect/test/user search
- Gmail: connect/disconnect/polling frequency
- Google Calendar: connect/disconnect with `transcripts_detected` warning badge
- Zoom: connect/disconnect with popup OAuth flow
- Notification bell: unread count badge, notification feed modal, mark read

**API services:** `slackService`, `gmailService`, `calendarService`, `zoomService`, `nudgeSettingsService`, `importService`, `authService`

---

### Phase 3A — Auth, Legal & Team Management

**Goal:** Production-ready auth (email verification, password reset), legal compliance (privacy policy + terms), and full team management before any design partner goes live.

---

#### Sprint 1 — Privacy Policy & Terms ✓ DONE

| Item | Status | Detail |
|---|---|---|
| Privacy Policy page | ✓ DONE | Static page at `/privacy` — built in Google AI Studio frontend |
| Terms of Service page | ✓ DONE | Static page at `/terms` — built in Google AI Studio frontend |
| Backend enforcement | ⏸ Deferred | `terms_accepted_at` field not added — frontend handles consent UX |

---

#### Sprint 2 — Email Verification on Registration ✓ DONE

OTP is sent on first registration to verify the email address is real. Login remains direct email+password → JWT.

**Email backend:** Amazon SES via SMTP (`email-smtp.us-east-1.amazonaws.com:587`). `DEFAULT_FROM_EMAIL = support@twocents.ai`. Domain `twocents.ai` verified in SES, production access granted (50k/day limit).

**New model: `EmailOTP`** (migration 0005)
```
id             UUIDField (PK)
user           ForeignKey(User)
code           CharField(6) — secrets.randbelow(1_000_000), zero-padded
purpose        CharField — 'email_verification' | 'password_reset'
created_at     DateTimeField(auto_now_add)
expires_at     DateTimeField — created_at + 10 minutes
used_at        DateTimeField(null) — set on successful verify
attempts       IntegerField(default=0) — max 5 before invalidated
```

**Registration flow:**
```
POST /auth/register/ {first_name, last_name, email, password, org_name, plan}
  → creates User(is_active=False) + Organisation + Person atomically
  → generates OTP(purpose='email_verification'), sends via SES
  → returns { verification_required: true, session_token: "<signed, 10-min expiry>" }

POST /auth/verify-email/ {session_token, code}
  → validates session_token (django.core.signing, salt='email-verify', max_age=600s)
  → finds inactive user, checks OTP code (max 5 attempts, 10-min expiry)
  → sets user.is_active=True, marks OTP used_at=now()
  → returns { access, refresh } JWT tokens
```

**Inactive user login (auto-redirect):**
```
POST /auth/token/ {email, password}
  → if user is inactive AND password is correct:
       generates fresh OTP, sends via SES
       returns { verification_required: true, session_token }
  → if user is active: returns { access, refresh } JWT tokens normally
  → if wrong password/unknown: 401
```

**Resend for stuck users** (login page "Activate your account" link):
```
POST /auth/resend-verification/ {email, password}
  → verifies credentials against inactive account
  → generates fresh OTP (invalidates previous), sends via SES
  → returns { verification_required: true, session_token }
```

**Invited users** (`/auth/invite/accept/`) created with `is_active=True` — no OTP needed (email verified implicitly via invite link).

**Endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register/` | POST | Create org + user (inactive) → send OTP |
| `/api/v1/auth/verify-email/` | POST | Validate OTP → activate account → JWT |
| `/api/v1/auth/resend-verification/` | POST | Re-send OTP for stuck unverified accounts |
| `/api/v1/auth/token/` | POST | Login — auto-redirects inactive users to OTP flow |

---

#### Sprint 3 — Forgot Password with Email OTP ✓ DONE

```
POST /auth/password/reset/ {email}
  → silent 200 (no enumeration) — sends OTP if email found and active

POST /auth/password/reset/confirm/ {email, otp, new_password}
  → validates OTP (max 5 attempts, 10-min expiry)
  → sets new password (min 8 chars)
  → blacklists all existing refresh tokens for that user
  → returns { detail: "Password reset successful." }
```

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/password/reset/` | POST | Send reset OTP (silent) |
| `/api/v1/auth/password/reset/confirm/` | POST | Validate OTP + set new password |

---

#### Sprint 4 — Invitations Management ✓ DONE

| Item | Detail |
|---|---|
| `GET /api/v1/auth/invitations/` | List all sent invitations with status (pending / accepted / expired). |
| `POST /api/v1/auth/invitations/{id}/resend/` | Re-send invite email, refresh 7-day token. |
| `DELETE /api/v1/auth/invitations/{id}/revoke/` | Revoke a pending invitation. |
| Frontend: Settings → Team tab | Members table (name, email, role, status) + invite form + resend/revoke on pending rows. |

---

#### Sprint 5 — Meetings Commitment Count ✓ DONE

| Item | Detail |
|---|---|
| `commitment_count` on `MeetingSerializer` | `Count('commitments')` annotation. Read-only field. |
| `pending_count` on `MeetingSerializer` | `Count('commitments', filter=Q(commitments__status='pending_review'))`. |
| Frontend: Meetings list | Each row shows `12 commitments · 3 pending review`. |

Both fields are implemented in `meetings/serializers.py` via `SerializerMethodField` on `MeetingSerializer`.

---

#### Sprint 6 — Meeting Ownership & Delegation ✓ DONE

**Goal:** Replace the flat "all org users see all meetings" model with a meeting-relative role model. Every meeting has an owner (its CoS). Access is scoped by ownership or accepted delegation. Action owners can see commitments they own without having full CoS access.

---

**Role model design:**

| Role | Who | What they can do |
|---|---|---|
| **CoS (meeting owner)** | `meeting.created_by == request.user` | Full CRUD on that meeting and all its commitments |
| **Delegate** | Accepted `MeetingManager` where `manager_user == request.user` | Same full access as CoS on the managed user's meetings |
| **Action owner** | `commitment.owner.user == request.user` | See and update their own commitments only; no access to other commitments in the same meeting |
| **Org admin** | `user.is_org_admin` | All access (existing behaviour preserved for admin operations) |

A user who creates their own meeting becomes its CoS automatically — there is no fixed "CoS role" on the User model.

---

**New field: `Meeting.created_by`**

```python
created_by = models.ForeignKey(
    'accounts.User',
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='owned_meetings',
)
```

- Added in `meetings/0005_meeting_created_by.py`
- RunPython backfill: sets `created_by` to the org's first admin user for all existing meetings
- All new meetings set `created_by = request.user` in the upload/import views

---

**New model: `MeetingManager`** (in `accounts/models.py`)

Two-sided delegation: delegator invites, delegatee must explicitly accept.

```python
class MeetingManager(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='meeting_managers')
    manager_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='manages_for')   # gets CoS access
    managed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delegated_to')  # whose meetings are shared
    status       = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table     = 'accounts_meetingmanager'
        unique_together = [['organisation', 'manager_user', 'managed_user']]
```

Migration: `accounts/0007_meetingmanager`

---

**Access rules (applied in ViewSet `get_queryset`):**

```python
# Meetings a user can manage
def _accessible_meeting_ids(user):
    """Returns Q filter for meetings this user has full CoS access to."""
    # Meetings they own directly
    owned = Q(created_by=user)
    # Meetings owned by users who have accepted delegation to this user
    delegated_from = MeetingManager.objects.filter(
        manager_user=user, status='accepted'
    ).values_list('managed_user_id', flat=True)
    delegated = Q(created_by_id__in=delegated_from)
    return owned | delegated

# Commitments a user can see (CoS access OR own commitment)
def _accessible_commitment_filter(user):
    cos_access  = Q(meeting__in=Meeting.objects.filter(_accessible_meeting_ids(user)))
    own_action  = Q(owner__user=user)
    return cos_access | own_action
```

**CommitmentEvent visibility for action owners:**
- Action owners (not CoS or delegate) who view `/commitments/{id}/history/` receive only events where `actor.user == request.user` — they see their own feedback submissions but NOT CoS actions (confirms, escalations, nudges).
- CoS and delegates see all events.

---

**New endpoints:**

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/managers/` | GET | Any user | List all delegations involving the current user (as delegator or delegatee) |
| `/api/v1/managers/` | POST | Any user | Delegator creates delegation request `{manager_user_id}` |
| `/api/v1/managers/{id}/accept/` | POST | Delegatee only | Accept a pending delegation |
| `/api/v1/managers/{id}/` | DELETE | Delegator or delegatee | Revoke (if delegator) or decline (if delegatee) |

**Updated existing endpoints:**

| Endpoint | Change |
|---|---|
| `POST /meetings/upload/` | Sets `meeting.created_by = request.user` |
| `POST /meetings/import/` | Sets `meeting.created_by = request.user` |
| `GET /meetings/` | Filters to accessible meetings only (owned + delegated) |
| `GET /commitments/` | Filters to accessible commitments (CoS access OR own action) |
| `GET /commitments/{id}/history/` | Action owners get filtered history (own events only) |
| `GET /dashboard/` | Scoped to accessible commitments |

**Action owner constraints:**
- Action owners can call `POST /commitments/{id}/log-update/` — writes a `CommitmentEvent` and triggers an in-app notification to the CoS.
- Action owners **cannot** call `confirm/`, `reject/`, `escalate/`, `resolve/`, or `reopen/` — all return 403.
- CoS sees all events in `/history/`; action owners see only events where `actor == themselves`.

**Notification on owner update:**
- `_notify_cos_of_owner_update(commitment, actor)` creates `InAppNotification(type=OWNER_UPDATE)` for the meeting's CoS whenever an action owner logs an update.
- Skips notification if the actor IS the CoS (prevents self-noise) or is an accepted delegate.
- `InAppNotification.Type.OWNER_UPDATE` added alongside existing `slack_reply`, `gmail_reply`, `meeting_ready`, `meeting_failed` types (migration `notifications/0010_inappnotification_owner_update`).

**Implementation files changed:**
- `accounts/models.py` — `MeetingManager` model
- `accounts/serializers.py` — `MeetingManagerSerializer`
- `accounts/views.py` — `MeetingManagerViewSet` (list, create, accept action, destroy)
- `accounts/urls.py` — router registration
- `accounts/admin.py` — `MeetingManagerAdmin`
- `meetings/models.py` — `created_by` FK on `Meeting`
- `meetings/views.py` — `_accessible_meeting_q()` helper + updated `get_queryset` + `created_by=request.user` in upload/import
- `commitments/views.py` — `_has_cos_access()` + `_notify_cos_of_owner_update()` + role-scoped queryset + 403 guards on status mutations + `history()` scoping
- `analytics/views.py` — role-scoped `DashboardView`
- `notifications/models.py` — `OWNER_UPDATE` notification type
- Migrations: `accounts/0007_meetingmanager`, `meetings/0007_meeting_created_by`, `notifications/0010_inappnotification_owner_update`

Committed as `feat(phase3a-sprint6): meeting ownership & delegation` (`5e568e8`).

---

### Phase 3B — Transcript Source Integrations ← NEXT

**Goal:** Ingest transcripts automatically from the tools CoS teams already use — without requiring Zoom cloud recording or Google Meet.

#### tl;dv

- **What it does:** Records and transcribes meetings (Zoom, Google Meet, Teams) as a bot participant. Exports VTT/SRT transcripts.
- **Integration approach:** tl;dv has a REST API. Poll for new meetings or receive webhook on `meeting.completed`. Download transcript via API token.
- **New model:** `TldvConnection` (per-org API key + last_synced_at) · `TldvRecording` (status machine, meeting FK)
- **New Celery task:** `sync_tldv_recordings` — every 15 min, fetch new recordings, create Meeting, queue `process_meeting`
- **Settings:** Connect via API key (no OAuth — tl;dv uses personal API tokens)
- **Endpoints:** `GET /tldv/status/` · `POST /tldv/connect/` · `POST /tldv/disconnect/`

#### Granola

- **What it does:** Mac desktop app that captures meeting audio and generates AI notes + transcript. Stores data locally and in cloud.
- **Integration approach:** Granola has a REST API (beta). Authenticate per-user, poll for new meeting notes, extract transcript text.
- **New model:** `GranolaConnection` (per-org API key) · `GranolaRecording`
- **New Celery task:** `sync_granola_recordings` — every 15 min
- **Endpoints:** `GET /granola/status/` · `POST /granola/connect/` · `POST /granola/disconnect/`

#### Fathom

- **What it does:** Records and transcribes Zoom/Meet/Teams calls. Sends email summaries with action items.
- **Integration approach:** Fathom has a webhook API. Register webhook endpoint to receive `call.completed` events with transcript URL. Download and process.
- **New model:** `FathomConnection` (per-org webhook secret + API key) · `FathomRecording`
- **Webhook endpoint:** `POST /fathom/webhook/` (HMAC verified)
- **Endpoints:** `GET /fathom/status/` · `POST /fathom/connect/` · `POST /fathom/disconnect/`

---

### Phase 3C — Productivity Tool Integrations

**Goal:** Push confirmed commitments into the tools teams already use for task management and docs.

#### Jira

- **What it does:** Push a confirmed Commitment as a Jira issue; sync status back when issue closes.
- **Integration approach:** Jira REST API v3. OAuth 2.0 (Atlassian) or API token per org. On commitment confirm → `POST /rest/api/3/issue`. Jira webhook → update commitment status when issue transitions.
- **New model:** `JiraConnection` (per-org API token + base URL + project key) · `JiraIssueLink` (commitment FK + jira_issue_key)
- **New endpoint:** `POST /api/v1/commitments/{id}/push-to-jira/`
- **Webhook:** `POST /api/v1/jira/webhook/` — maps issue status → commitment status
- **Settings:** Connect via Jira API token + base URL; pick default project

#### Notion AI

- **What it does:** Pull action items / commitments from Notion pages (meeting notes databases); push confirmed commitments back as Notion database rows.
- **Integration approach:** Notion API (OAuth). Read from a user-selected database; detect action item patterns; create Notion database rows for confirmed commitments.
- **New model:** `NotionConnection` (per-org OAuth token + workspace) · `NotionPageLink` (meeting FK + notion_page_id)
- **New Celery task:** `sync_notion_pages` — poll selected Notion database for new meeting note pages, import transcript text, queue `process_meeting`
- **Settings:** OAuth connect → pick Notion workspace + database to monitor
- **Endpoints:** `GET /notion/status/` · `GET /notion/oauth/start/` · `GET /notion/oauth/callback/` · `POST /notion/disconnect/`

---

### Phase 4 — Intelligence Layer (after 3 paying design partners)

| Feature | What it unlocks |
|---|---|
| Analytics endpoints — delivery rates by person/team/period | `feature/analytics` |
| Conflict detection — pgvector embeddings + Gemini Flash classification | `feature/conflicts` |
| Person knowledge graph — graph API + frontend rendering | `feature/person-graph` |
| Org calibration — recompile from ExtractionFeedback signals weekly | `feature/calibration` |
| Nudge intelligence — CoS review queue for ambiguous replies | `feature/nudge-intelligence` |
| Friction detection — cross-functional blockade signals from replies | `feature/friction` |
| Org health heatmap — departmental delivery rate grid | `feature/org-health` |
| Executive brief — AI-synthesised strategic pillar summaries | `feature/exec-brief` |

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
  GET    /auth/me/                  Current user profile + org {id, email, name, is_org_admin, organisation}
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
  POST   /commitments/{id}/nudge/      Send nudge {method: slack|email|phone|in_person|other, note?}; logs CommitmentEvent(nudged)
  POST   /commitments/{id}/log-update/ Log owner response {response, new_status?}; logs CommitmentEvent(field_edited)
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
  GET    /slack/oauth/start/        Redirect to Slack OAuth — accepts ?auth=<JWT> for browser-redirect flows
  GET    /slack/oauth/callback/     OAuth callback — save per-org token
  GET    /slack/users/              Search Slack workspace by email or name (?q=)
  POST   /slack/users/import/       Import selected Slack users as Persons (link or create)
  GET    /slack/users/sync/         Full workspace sync — matched/unmatched Persons vs Slack members
  POST   /slack/users/sync/         Confirm matches {confirmations: [{person_id, slack_user_id}]}

MANAGERS (Delegation)
  GET    /managers/                 List delegations for current user (as delegator or delegatee)
  POST   /managers/                 Create delegation request {manager_user_id}
  POST   /managers/{id}/accept/     Delegatee accepts pending delegation
  DELETE /managers/{id}/            Delegator revokes OR delegatee declines

NUDGE SETTINGS
  GET    /nudge-settings/           Org nudge schedule {nudge_enabled, first_days_before, second_hours_before}
  PATCH  /nudge-settings/           Update schedule (first_days_before: 1/2/5, second_hours_before: 24/48/72)

GMAIL
  GET    /gmail/status/             {connected, email} — is org's Gmail connected?
  GET    /gmail/oauth/start/        Redirect to Google OAuth — accepts ?auth=<JWT>
  GET    /gmail/oauth/callback/     OAuth callback — stores access + refresh token on org
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
