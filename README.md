# Verato

Accountability layer for organisations. Extracts every commitment made in meetings, assigns it an owner, scores risk, and nudges before it slips.

---

## What is this?

A Chief of Staff sits in 10–15 meetings a week. Every meeting produces commitments — "I'll get you the numbers by Thursday", "we'll have a proposal ready end of month", "John's team will send the draft by Friday." These promises are made verbally, captured nowhere, and followed up manually.

The result: hours spent chasing people, things slipping through the cracks, and the CoS finding out too late to intervene.

Verato fixes this. Connect your Google Meet or Zoom account once. When a meeting ends, Verato pulls the transcript, sends it to Gemini AI, and extracts every commitment — who promised what, to whom, by when. It scores each one for risk, sends automatic nudges to owners via Slack or Gmail, and reads their replies to update status automatically. When something is about to slip, the CoS knows before it does.

**Who it's for:** Chiefs of Staff, Executive Assistants, and Heads of Operations at companies of 20–200 people who are managing commitments across a leadership team and currently doing it in spreadsheets or nothing at all.

**What's built:**
- Google Meet + Zoom auto-ingestion — meetings processed within 15 minutes of ending
- Gemini AI commitment extraction with owner, deadline, and confidence score
- Risk scoring with full breakdown (deadline proximity, owner track record, update recency)
- Slack and Gmail nudges with automatic reply parsing
- Strategic Initiatives — group commitments by theme with AI-generated health summaries
- In-app notifications, delegation, team management, and a full audit trail per commitment

---

**Stack:** Django REST API · React/Vite · PostgreSQL · Redis · Celery · Gemini AI · Slack · Gmail OAuth · Google Calendar · Google Meet · Zoom
**Licence:** AGPL-3.0
**Repo:** https://github.com/kanags76/Verato
**Production:** https://api.verato.twocents.ai (backend) · https://verato.twocents.ai (frontend)

---

## Project Structure

```
Verato/
├── backend/                   Django project
│   ├── apps/
│   │   ├── accounts/          Organisation, User (is_org_admin), Person, Invitation, MeetingManager
│   │   ├── meetings/          Meeting, MeetingParticipant, MeetingTopic
│   │   ├── commitments/       Commitment, CommitmentTag (+ is_initiative), EscalationEvent, CommitmentEvent, risk.py
│   │   ├── notifications/     Slack nudges, Gmail OAuth, Google Calendar, Zoom, NudgeLog, GmailPollLog, CalendarConnection, CalendarEvent, ZoomConnection, ZoomRecording, InAppNotification, weekly digest
│   │   ├── prompts/           Editable Gemini prompts in DB + AICallLog (full history of every AI call)
│   │   └── analytics/         Dashboard summary (overdue / at-risk / on-track counts)
│   ├── extraction/            AI extraction engine (pure Python, no Django dependency)
│   │   ├── extractor.py       extract_commitments() — transcript → {commitments, topics, meeting_type, summary}
│   │   ├── importer.py        extract_from_document() — prior tracker → same dict format
│   │   ├── prompt_builder.py  Gemini prompts for transcript + import
│   │   ├── parser.py          safe_json_parse() + parse_extraction_response()
│   │   └── tests/
│   │       ├── fixtures/      5 transcript + 3 import document fixtures
│   │       ├── test_parser.py
│   │       ├── test_extractor.py
│   │       └── test_importer.py
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   └── celery.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env                   (gitignored — never commit)
├── frontend/                  React 19 + Vite + TypeScript + Tailwind v4
│   ├── src/
│   │   ├── screens/           Dashboard, CommitmentDetail, Meetings, MeetingDetail, People, Settings, Initiatives, InitiativeDetail, Login, Register, ActivateAccount
│   │   │   └── onboarding/    ConnectSlack, ImportTracker
│   │   ├── components/        UploadModal, ClarificationModal, LinkSlackPeopleModal, DelegationManagement, ErrorProvider, layout/, ui/
│   │   ├── contexts/          AuthContext (JWT + silent refresh)
│   │   └── lib/
│   │       ├── api/           client.ts (Axios), services.ts, auth.ts
│   │       └── utils.ts
│   ├── .env.local             (gitignored — never commit)
│   └── .env.local.template    Reference — copy and fill in
└── AI Build Prompt/           Planning docs
```

---

## Local Dev — Start of Session

### Step 1 — Verify background services

```bash
brew services list | grep -E "postgresql|redis"
pg_isready        # → localhost:5432 - accepting connections
redis-cli ping    # → PONG

# Start if either is stopped:
brew services start postgresql@18
brew services start redis
```

### Step 2 — Open five terminal tabs

**Tab 1 — Django API** (http://localhost:8000)
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver
```

**Tab 2 — Celery worker**
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
celery -A config worker --loglevel=info
```

**Tab 3 — React/Vite frontend** (http://localhost:5173)
```bash
cd ~/Documents/Programs/Verato/frontend
npm run dev
```

**Tab 4 — Tests**
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
pytest -v --tb=short
```

**Tab 5 — Git / shell** (free tab)

### End of session

Stop Ctrl+C in tabs 1–3. PostgreSQL and Redis can stay running.

---

## Localhost URLs

| URL | What it is |
|---|---|
| `http://localhost:5173/` | **Frontend — main app entry point** |
| `http://localhost:8000/api/health/` | Backend health check → `{"status": "ok"}` |
| `http://localhost:8000/admin/` | Django admin |
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — API test interface** |

---

## API Endpoints

### Authenticating in Swagger UI

```
1. POST /api/v1/auth/token/ → {"email": "admin@example.com", "password": "admin1234"}
2. Copy the "access" value
3. Click Authorize (top right) → enter: Bearer <token>
```

### Full API Surface

| Endpoint | Method | Description |
|---|---|---|
| **Auth** | | |
| `/api/v1/auth/register/` | POST | Register new org + admin user → JWT + `is_first_login: true` |
| `/api/v1/auth/invite/` | POST | Org admin sends email invite |
| `/api/v1/auth/invite/validate/` | GET | `?token=` — validate invite token |
| `/api/v1/auth/invite/accept/` | POST | Accept invite, create account → JWT |
| `/api/v1/auth/invitations/` | GET | List all sent invitations (admin only) |
| `/api/v1/auth/invitations/{id}/resend/` | POST | Re-send invite email, refresh 7-day token |
| `/api/v1/auth/invitations/{id}/revoke/` | DELETE | Revoke a pending invitation |
| `/api/v1/auth/token/` | POST | Login with email + password → JWT |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT |
| `/api/v1/auth/logout/` | POST | Blacklist refresh token |
| `/api/v1/auth/me/` | GET | Current user profile + org |
| **Org** | | |
| `/api/v1/orgs/` | GET | List orgs accessible to current user |
| `/api/v1/orgs/{id}/settings/` | PATCH | Update org settings |
| **Dashboard** | | |
| `/api/v1/dashboard/` | GET | `{overdue, at_risk, on_track, total_active}` |
| **Meetings** | | |
| `/api/v1/meetings/` | GET | List org meetings |
| `/api/v1/meetings/upload/` | POST | Upload transcript → 202 + meeting_id |
| `/api/v1/meetings/import/` | POST | Upload prior tracker doc → 202 + meeting_id |
| `/api/v1/meetings/{id}/` | GET/PATCH | Meeting detail / update title, date, type, summary |
| `/api/v1/meetings/{id}/status/` | GET | Poll processing status |
| `/api/v1/meetings/{id}/participants/` | GET | List participants |
| `/api/v1/meetings/{id}/add-participant/` | POST | Add person to meeting |
| `/api/v1/meetings/{id}/remove-participant/` | POST | Remove person |
| `/api/v1/meetings/{id}/link-participants/` | POST | Validate Gemini-detected participants |
| **Commitments** | | |
| `/api/v1/commitments/` | GET | List with filters: `?status= ?owner= ?priority= ?tags__label= ?deadline_before= ?risk_gte= ?meeting=` |
| `/api/v1/commitments/{id}/` | GET/PATCH | Detail / update text, owner, deadline, priority, tags |
| `/api/v1/commitments/bulk-confirm/` | POST | Confirm all PENDING_REVIEW; optional `{meeting?, min_confidence?}` |
| `/api/v1/commitments/{id}/confirm/` | POST | PENDING_REVIEW → ACTIVE |
| `/api/v1/commitments/{id}/reject/` | POST | → CANCELLED + ExtractionFeedback |
| `/api/v1/commitments/{id}/escalate/` | POST | → ESCALATED + EscalationEvent |
| `/api/v1/commitments/{id}/resolve/` | POST | `{outcome: done\|deferred\|cancelled, note?, new_deadline?}` |
| `/api/v1/commitments/{id}/reopen/` | POST | Reopen closed commitment → ACTIVE |
| `/api/v1/commitments/{id}/nudge/` | POST | `{method: slack\|email\|phone\|in_person\|other, note?}` — email sends from org Gmail |
| `/api/v1/commitments/{id}/log-update/` | POST | Log manual follow-up response |
| `/api/v1/commitments/{id}/history/` | GET | Full audit log — newest first |
| **Tags** | | |
| `/api/v1/tags/` | GET | List all org tags with id, label, usage, is_initiative, description |
| `/api/v1/tags/search/` | GET | Tag autocomplete ranked by usage; `?q=` prefix filter |
| `/api/v1/tags/{id}/` | GET/PATCH | Tag detail / rename, promote to initiative, set description (admin only) |
| `/api/v1/tags/{id}/merge/` | POST | Merge into another tag `{into: "label"}` — re-tags all commitments (admin only) |
| `/api/v1/tags/{id}/generate-summary/` | POST | Gemini AI summary for initiative tag; skips if summary < 12h old and no updates; `?force=true` overrides |
| **Initiatives** | | |
| `/api/v1/initiatives/` | GET | Strategic initiatives (is_initiative tags) with per-status commitment counts and AI summary |
| **Auto-tag** | | |
| `/api/v1/commitments/{id}/auto-tag/` | POST | Gemini suggests and applies 1–4 tags from org tag library |
| **Delegation** | | |
| `/api/v1/managers/` | GET | List delegations involving current user (as delegator or delegatee) |
| `/api/v1/managers/` | POST | Create delegation request `{manager_user_id}` — current user is delegator |
| `/api/v1/managers/{id}/accept/` | POST | Delegatee accepts a pending delegation |
| `/api/v1/managers/{id}/` | DELETE | Revoke (delegator) or decline (delegatee) a delegation |
| `/api/v1/managers/{id}/accept/` | POST | Delegatee accepts a pending delegation |
| **Persons** | | |
| `/api/v1/persons/` | GET/POST | List or create persons |
| `/api/v1/persons/{id}/` | GET/PATCH | Detail / update name, email, role |
| `/api/v1/persons/{id}/timeline/` | GET | Meeting history + commitments |
| `/api/v1/persons/{id}/topics/` | GET | Topic frequency list |
| `/api/v1/persons/{id}/link-slack/` | POST | Link Slack user ID |
| `/api/v1/persons/merge/` | POST | Deduplicate: `{primary_id, duplicate_ids[]}` |
| **Slack** | | |
| `/api/v1/slack/status/` | GET | `{connected, workspace_id, workspace_name}` |
| `/api/v1/slack/disconnect/` | POST | Remove org Slack token |
| `/api/v1/slack/test-message/` | POST | Send test DM to requesting user |
| `/api/v1/slack/actions/` | POST | Interactive button webhook (Done/Delayed/Blocked) → instant commitment update + in-app notification |
| `/api/v1/slack/oauth/start/` | GET | Redirect to Slack OAuth consent |
| `/api/v1/slack/oauth/callback/` | GET | Slack OAuth callback |
| `/api/v1/slack/users/` | GET | Search workspace users `?q=email_or_name` |
| `/api/v1/slack/users/import/` | POST | Import Slack users as Persons |
| `/api/v1/slack/users/sync/` | GET/POST | Full workspace sync / confirm matches |
| **Nudge Settings** | | |
| `/api/v1/nudge-settings/` | GET/PATCH | Nudge schedule: `{nudge_enabled, first_days_before, second_hours_before}` |
| **Gmail** | | |
| `/api/v1/gmail/status/` | GET | `{connected, email}` |
| `/api/v1/gmail/disconnect/` | POST | Remove org Gmail tokens |
| `/api/v1/gmail/oauth/start/` | GET | Redirect to Google OAuth consent |
| `/api/v1/gmail/oauth/callback/` | GET | Gmail OAuth callback — stores per-org access + refresh tokens |
| **Notifications** | | |
| `/api/v1/notifications/` | GET | Last 50 in-app notifications for current user (user-scoped, not org-wide) |
| `/api/v1/notifications/unread-count/` | GET | `{unread: N}` — for badge |
| `/api/v1/notifications/<id>/read/` | POST | Mark one notification as read |
| `/api/v1/notifications/mark-all-read/` | POST | Clear all unread badges |
| **Google Calendar** | | |
| `/api/v1/calendar/status/` | GET | `{connected, email, transcripts_detected}` |
| `/api/v1/calendar/oauth/start/` | GET | Redirect to Google Calendar OAuth consent (`?auth=<jwt>`) |
| `/api/v1/calendar/oauth/callback/` | GET | Calendar OAuth callback — stores per-org access + refresh tokens |
| `/api/v1/calendar/disconnect/` | POST | Remove org Calendar connection |
| **Zoom** | | |
| `/api/v1/zoom/status/` | GET | `{connected, email, account_id}` |
| `/api/v1/zoom/oauth/start/` | GET | Redirect to Zoom OAuth consent (`?auth=<jwt>`) |
| `/api/v1/zoom/oauth/callback/` | GET | Zoom OAuth callback — stores per-org tokens |
| `/api/v1/zoom/disconnect/` | POST | Remove org Zoom connection |
| `/api/v1/zoom/webhook/` | POST | Zoom webhook receiver — HMAC verified; handles `recording.completed` |

---

## Running Tests

```bash
# All tests
pytest -v --tb=short

# With real Gemini calls (needs GEMINI_API_KEY)
pytest -v --tb=short --run-slow

# Specific app
pytest apps/accounts/tests/ -v
pytest apps/commitments/ -v
pytest -k "test_risk" -v

# With coverage
pytest --cov=apps --cov=extraction --cov-report=html
```

---

## Infrastructure

| Service | Version | Address | Managed by |
|---|---|---|---|
| PostgreSQL | 18.3 | localhost:5432 | Homebrew |
| Redis | 7.x | localhost:6379 | Homebrew |
| Gemini AI | 2.5 Flash Lite | google.genai SDK | `GEMINI_API_KEY` |

---

## Build Progress

| Milestone | Feature | Status |
|---|---|---|
| W1 | Extraction engine (transcript + import) | ✓ Done |
| W2 | Django models + API skeleton | ✓ Done |
| W3 | Ingestion pipeline + prior import | ✓ Done |
| W3.5 | Knowledge graph (tags, topics, person lineage) | ✓ Done |
| W4 | Commitment actions + dashboard API | ✓ Done |
| W5 | Risk scoring + status automation | ✓ Done |
| W6 | Slack nudges + weekly digest email | ✓ Done |
| W6.5 | Self-serve sign-up, team invites, per-org Slack OAuth | ✓ Done |
| W7 | API gap-fill — bulk-confirm, nudge, tag autocomplete | ✓ Done |
| W8 | API hardening — audit log, person CRUD/merge, reopen, logout | ✓ Done |
| W9 | Production — Slack OAuth JWT flow, `/auth/me/`, Django admin pipeline dashboard | ✓ Done |
| W10 | Nudge engine — configurable schedule, NudgeLog, CoS escalation | ✓ Done |
| W11 | Slack user management — workspace search, import, full sync | ✓ Done |
| W12 | Gmail OAuth — send nudge emails, poll reply threads, Gemini intent parsing | ✓ Done |
| W12.5 | Admin — per-org Gmail polling frequency, prompts in DB | ✓ Done |
| W13 | React/Vite frontend committed (Google AI Studio build) | ✓ Done |
| W13.5 | In-app notification feed (Slack + Gmail reply triggers) | ✓ Done |
| W13.6 | Bug fixes — email uniqueness 400, Gmail poll deduplication, Gemini SDK migration | ✓ Done |
| W14 | Google Calendar + Google Meet passive ingestion — CalendarConnection, CalendarEvent, sync + fetch tasks, admin | ✓ Done |
| W14.5 | Gemini auto-title, optional meeting title on upload + import, OAUTHLIB_RELAX_TOKEN_SCOPE fix | ✓ Done |
| W15 | Zoom OAuth + webhook + recording transcript pipeline — ZoomConnection, ZoomRecording, fetch task, admin | ✓ Done |
| W15.5 | Slack user management — workspace search, import, full workspace sync | ✓ Done |
| W16 | Frontend: Zoom + Calendar settings cards, notification bell, all screens complete | ✓ Done |
| W17 | Phase 3A Sprint 1–2: Privacy/Terms pages, email verification on registration (SES OTP) | ✓ Done |
| W17.5 | Phase 3A Sprint 3–4: Forgot-password OTP flow, invitation resend/revoke | ✓ Done |
| W18 | Phase 3A Sprint 5–6: Meetings commitment count, meeting ownership & delegation | ✓ Done |
| W18.5 | Sprint 6 frontend: delegation UI, role-aware commitment actions, OTP registration flow, ActivateAccount screen | ✓ Done |
| W19 | User-scoped notifications: `recipient_user` FK on `InAppNotification`, `COMMITMENT_CLOSED` + `DELEGATION_INVITE` types, routing rules per notification type, delegation invite email + in-app | ✓ Done |
| W20 | Strategic Initiatives: `CommitmentTag` promoted to initiative (`is_initiative`, `description`, `ai_summary`); tag CRUD + merge API; `GET /initiatives/` with per-status counts; `POST auto-tag` (Gemini); AI summary with staleness guard (12h + no updates) | ✓ Done |
| W20.5 | AI call logging: `AICallLog` model captures every Gemini call — prompt name/version, input, output, duration, success, error, linked domain objects; all 8 call sites instrumented; `weekly_digest_intro` prompt moved to DB | ✓ Done |
| W20.6 | Risk score breakdown: `compute_risk_breakdown()` + `risk_breakdown` serializer field exposes 3-component breakdown (deadline proximity, owner track record, update recency) per commitment | ✓ Done |

```
PHASE 1 — Backend (W1–W7)            ✓ COMPLETE
PHASE 2 — Frontend scaffold           ✓ COMPLETE (React/Vite on Cloud Run)
PHASE 2.5 — Production hardening      ✓ COMPLETE (live at api.verato.twocents.ai)
PHASE 2.6 — Nudge engine + Gmail      ✓ COMPLETE
PHASE 2.7 — In-app notifications      ✓ COMPLETE
PHASE 2.8 — Passive ingestion         ✓ COMPLETE (Google Meet + Zoom auto-processing)
PHASE 2.9 — Frontend integrations UI  ✓ COMPLETE (Calendar + Zoom cards, notification bell)
PHASE 3A — Auth, Legal & Team Mgmt    ✓ COMPLETE (email verify, password reset, invitations, ownership, user-scoped notifications)
PHASE 3B — Strategic Intelligence     ✓ COMPLETE (initiatives, tag management, auto-tag, AI call logging, risk breakdown)
PHASE 3C — Transcript Sources         ← Next (tl;dv, Granola, Fathom, Teams)
```

---

## Contributing

This project is open source under the AGPL-3.0 licence. Contributions are welcome.

- `main` is a protected branch — all changes must come in via a pull request
- Fork the repo, create a feature branch, and open a PR against `main`
- Keep PRs focused — one feature or fix per PR

---

## Environment Variables

### Backend — `backend/.env` (gitignored)

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Required |
| `DB_*` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `GEMINI_API_KEY` | Google AI Studio key |
| `GEMINI_EXTRACTION_MODEL` | `gemini-2.5-flash-lite` |
| `APP_BASE_URL` | Frontend URL for invite links |
| `SLACK_BOT_TOKEN` | Global fallback bot token |
| `SLACK_SIGNING_SECRET` | Verifies Slack webhooks |
| `SLACK_CLIENT_ID` | Slack OAuth app |
| `SLACK_CLIENT_SECRET` | Slack OAuth app |
| `SLACK_OAUTH_REDIRECT_URI` | `/api/v1/slack/oauth/callback/` |
| `EMAIL_HOST` | `email-smtp.us-east-1.amazonaws.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | AWS SES SMTP username |
| `EMAIL_HOST_PASSWORD` | AWS SES SMTP password |
| `DEFAULT_FROM_EMAIL` | `support@twocents.ai` (domain verified in SES) |
| `GOOGLE_CLIENT_ID` | Google Cloud OAuth 2.0 client |
| `GOOGLE_CLIENT_SECRET` | Google Cloud OAuth 2.0 client |
| `GOOGLE_GMAIL_REDIRECT_URI` | `/api/v1/gmail/oauth/callback/` |
| `GOOGLE_CALENDAR_REDIRECT_URI` | `/api/v1/calendar/oauth/callback/` |
| `ZOOM_CLIENT_ID` | Zoom Marketplace app |
| `ZOOM_CLIENT_SECRET` | Zoom Marketplace app |
| `ZOOM_WEBHOOK_SECRET` | Zoom Event Subscriptions secret token |
| `ZOOM_OAUTH_REDIRECT_URI` | `/api/v1/zoom/oauth/callback/` |
| `FRONTEND_URL` | Frontend base URL used in notification emails (default `https://app.twocents.ai`) |

### Frontend — `frontend/.env.local` (gitignored)

| Variable | Notes |
|---|---|
| `VITE_API_URL` | Django API base URL — `http://localhost:8000/api/v1` for local, `https://api.verato.twocents.ai/api/v1` for production |
