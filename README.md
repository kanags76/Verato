# Verato

Accountability layer for organisations. Extracts every commitment made in meetings, assigns it an owner, scores risk, and nudges before it slips.

**Stack:** Django REST API · Next.js · PostgreSQL · Redis · Celery · Gemini AI · Slack · Gmail OAuth
**Repo:** https://github.com/kanags76/Verato (private)

---

## Project Structure

```
Verato/
├── backend/                   Django project
│   ├── apps/
│   │   ├── accounts/          Organisation, User (is_org_admin), Person, Invitation
│   │   ├── meetings/          Meeting (meeting_type, summary), MeetingParticipant, MeetingTopic
│   │   ├── commitments/       Commitment, CommitmentTag (M2M, org-scoped), EscalationEvent, risk.py
│   │   ├── notifications/     Slack nudges, Gmail OAuth, NudgeLog, GmailPollLog, weekly digest
│   │   ├── prompts/           Editable Gemini prompts stored in DB (transcript, import, gmail_reply_parse)
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
├── frontend/                  Next.js 16 app
│   ├── app/
│   │   ├── (auth)/            Unauthenticated shell — login, register, invite
│   │   ├── (app)/             Authenticated shell — sidebar layout
│   │   │   ├── dashboard/     Stat cards, commitment list, filters
│   │   │   ├── commitments/   [id]/ — detail, edit, actions
│   │   │   ├── meetings/      Meeting list + status
│   │   │   ├── people/        Team members + delivery stats
│   │   │   ├── review/        [meetingId]/ — extraction review queue
│   │   │   ├── upload/        Transcript upload
│   │   │   └── settings/      Org, Slack, Team (tabbed)
│   │   └── onboarding/        Post-signup wizard (Slack → Import → Done)
│   ├── components/
│   │   ├── layout/            Sidebar
│   │   └── ui/                Button, Badge, Avatar, Input, Select, Spinner
│   ├── lib/
│   │   ├── api/               Typed wrappers: auth, commitments, meetings, people, slack, tags, orgs, dashboard
│   │   ├── auth.ts            tokenStore — localStorage + cookie dual write for proxy auth
│   │   └── types.ts           TypeScript interfaces matching Django serializer fields exactly
│   ├── proxy.ts               Auth gate — redirects unauthenticated requests to /login
│   └── .env.local             (gitignored — never commit)
└── AI Build Prompt/           Planning docs
```

---

## Local Dev — Start of Session

### Step 1 — Verify background services (run once, any terminal)

```bash
brew services list | grep -E "postgresql|redis"
pg_isready        # → localhost:5432 - accepting connections
redis-cli ping    # → PONG

# Start if either is stopped:
brew services start postgresql@18
brew services start redis
```

### Step 2 — Open five terminal tabs and run one command in each

**Tab 1 — Django API** (http://localhost:8000)
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver
```

**Tab 2 — Celery worker** (background task processor)
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
celery -A config worker --loglevel=info
```

**Tab 3 — Next.js frontend** (http://localhost:3000)
```bash
cd ~/Documents/Programs/Verato/frontend
npm run dev
```

**Tab 4 — Tests** (run as needed)
```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
pytest -v --tb=short
```

**Tab 5 — Git / shell** (free for git, manage.py commands, etc.)
```bash
cd ~/Documents/Programs/Verato
```

### End of session

**Always stop** (Ctrl+C in each tab):
```
Tab 1 — Ctrl+C   # stops Django API
Tab 2 — Ctrl+C   # stops Celery worker
Tab 3 — Ctrl+C   # stops Next.js dev server
```

**Leave running** (PostgreSQL and Redis auto-start on login and are lightweight):
```bash
# Nothing to do — they stay up across sessions and reboots
brew services list | grep -E "postgresql|redis"   # confirm if unsure
```

**Stop services only if** you're done for the day and want to free resources:
```bash
brew services stop postgresql@18
brew services stop redis
```

---

## Localhost URLs

| URL | What it is |
|---|---|
| `http://localhost:3000/` | **Frontend — main app entry point** |
| `http://localhost:3000/login` | Login page |
| `http://localhost:3000/register` | Plan picker + sign-up |
| `http://localhost:3000/dashboard` | Dashboard (requires auth) |
| `http://localhost:8000/api/health/` | Backend health check → `{"status": "ok"}` |
| `http://localhost:8000/admin/` | Django admin (admin / admin1234) |
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — API test interface** |
| `http://localhost:8000/api/schema/redoc/` | ReDoc — clean API docs |
| `http://localhost:8000/api/schema/` | Raw OpenAPI JSON |
| `http://localhost:8000/__debug__/` | Django debug toolbar (local only) |
| `http://localhost:8000/admin/meetings/meeting/pipeline-status/` | **Pipeline Status dashboard** — queue depths, stuck/failed meetings |

---

## API Endpoints

### Authenticating in Swagger UI

```
1. POST /api/v1/auth/token/ → {"email": "admin@example.com", "password": "admin1234"}
2. Copy the "access" value
3. Click Authorize (top right) → enter: Bearer <token>
4. All subsequent calls are authenticated
```

### Full API Surface

| Endpoint | Method | Description |
|---|---|---|
| **Auth** | | |
| `/api/v1/auth/register/` | POST | Register new org + admin user + person → JWT + `is_first_login: true` |
| `/api/v1/auth/invite/` | POST | Org admin sends email invite to a colleague |
| `/api/v1/auth/invite/validate/` | GET | `?token=` — validate invite token, returns email + org name |
| `/api/v1/auth/invite/accept/` | POST | Accept invite, create account → JWT tokens |
| `/api/v1/auth/invitations/` | GET | List all sent invitations with status (admin only) |
| `/api/v1/auth/token/` | POST | Login with email + password → JWT tokens |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT |
| `/api/v1/auth/logout/` | POST | Logout — blacklists refresh token before clearing session |
| `/api/v1/auth/me/` | GET | Current user profile + org (`{id, email, name, is_org_admin, organisation}`) |
| **Org** | | |
| `/api/v1/orgs/` | GET | List orgs accessible to current user |
| `/api/v1/orgs/{id}/settings/` | PATCH | Update org settings: `confidence_threshold`, `nudge_hours_before`, `digest_day`, `digest_hour` |
| **Dashboard** | | |
| `/api/v1/dashboard/` | GET | `{overdue, at_risk, on_track, total_active}` |
| **Meetings** | | |
| `/api/v1/meetings/` | GET | List org meetings (includes `commitment_count`, `pending_count`) |
| `/api/v1/meetings/upload/` | POST | Upload transcript text or file → 202 + meeting_id; Gemini extracts commitments + participants async |
| `/api/v1/meetings/import/` | POST | Upload prior tracker doc → 202 + meeting_id |
| `/api/v1/meetings/{id}/` | GET | Meeting detail |
| `/api/v1/meetings/{id}/` | PATCH | Update meeting title, date, meeting_type, or summary |
| `/api/v1/meetings/{id}/status/` | GET | Poll processing status; includes `participant_count`, `confirmed_count` |
| `/api/v1/meetings/{id}/participants/` | GET | List meeting participants with `confirmed` flag and `speaker_label` |
| `/api/v1/meetings/{id}/add-participant/` | POST | Add a person to this meeting (`{person_id}` or `{person: {name, email?, role?}}`) |
| `/api/v1/meetings/{id}/remove-participant/` | POST | Remove a person from this meeting (`{person_id}`) → 204 |
| `/api/v1/meetings/{id}/link-participants/` | POST | Validate Gemini-detected participants: link to existing person, create new, or skip |
| `/api/v1/meetings/zoom/webhook/` | POST | Zoom auto-ingest (stretch) |
| **Commitments** | | |
| `/api/v1/commitments/` | GET | List with filters: `?status=` `?owner=` `?priority=` `?source=` `?tags__label=` `?deadline_before=` `?risk_gte=` `?meeting=` |
| `/api/v1/commitments/{id}/` | GET | Detail (includes `tags[]`, `escalations[]`, `history[]`) |
| `/api/v1/commitments/{id}/` | PATCH | Update `normalised_text`, `owner`, `deadline`, `priority`, `tags` — all changes logged to history |
| `/api/v1/commitments/bulk-confirm/` | POST | Confirm all PENDING_REVIEW; optional `{meeting?, min_confidence?}` |
| `/api/v1/commitments/{id}/confirm/` | POST | PENDING_REVIEW → ACTIVE |
| `/api/v1/commitments/{id}/reject/` | POST | → CANCELLED + logs ExtractionFeedback |
| `/api/v1/commitments/{id}/escalate/` | POST | → ESCALATED + EscalationEvent; accepts `{message}` |
| `/api/v1/commitments/{id}/resolve/` | POST | `{outcome: done\|deferred\|cancelled, note?, new_deadline?}` |
| `/api/v1/commitments/{id}/reopen/` | POST | Reopen a closed (done/deferred/cancelled) commitment → ACTIVE |
| `/api/v1/commitments/{id}/nudge/` | POST | Send nudge to owner — `{method: slack\|email\|phone\|in_person\|other, note?}` — email sends from org's Gmail |
| `/api/v1/commitments/{id}/log-update/` | POST | Log owner response after manual follow-up — `{response, new_status?}` |
| `/api/v1/commitments/{id}/history/` | GET | Unified audit log: status changes, field edits, nudges, escalations — newest first |
| **Tags** | | |
| `/api/v1/tags/` | GET | Tag autocomplete ranked by usage; `?q=` for prefix filter |
| **Persons** | | |
| `/api/v1/persons/` | GET | List org participants |
| `/api/v1/persons/` | POST | Create a new person in the org (`{name, email?, role?}`) |
| `/api/v1/persons/{id}/` | GET | Person detail + delivery stats + meeting lineage |
| `/api/v1/persons/{id}/` | PATCH | Update name, email, or role |
| `/api/v1/persons/{id}/timeline/` | GET | Chronological meeting history with commitments + topics |
| `/api/v1/persons/{id}/topics/` | GET | Topic frequency list `[{label, count, last_seen}]` |
| `/api/v1/persons/{id}/link-slack/` | POST | Link Slack user ID to this person |
| `/api/v1/persons/merge/` | POST | Deduplicate persons: `{primary_id, duplicate_ids[]}` — reassigns all commitments, meetings, events to primary |
| **Slack** | | |
| `/api/v1/slack/status/` | GET | Is org's Slack connected? Returns `{connected, workspace_id, workspace_name}` |
| `/api/v1/slack/test-message/` | POST | Send a test DM to the requesting user's linked Slack account |
| `/api/v1/slack/actions/` | POST | Slack interactive button handler (Done/Delayed/Blocked) |
| `/api/v1/slack/oauth/start/` | GET | Redirect to Slack OAuth consent — accepts `?auth=<JWT>` for browser-redirect flows |
| `/api/v1/slack/oauth/callback/` | GET | Slack OAuth callback — stores per-org bot token |
| `/api/v1/slack/users/` | GET | Search Slack workspace users by email or name — `?q=` |
| `/api/v1/slack/users/import/` | POST | Import selected Slack users as Persons (link or create) |
| `/api/v1/slack/users/sync/` | GET | Full workspace sync — matched/unmatched Persons vs Slack members |
| `/api/v1/slack/users/sync/` | POST | Confirm sync matches — `{confirmations: [{person_id, slack_user_id}]}` |
| **Nudge Settings** | | |
| `/api/v1/nudge-settings/` | GET | Get org nudge schedule: `{nudge_enabled, first_days_before, second_hours_before}` |
| `/api/v1/nudge-settings/` | PATCH | Update nudge schedule — `first_days_before` (1/2/5), `second_hours_before` (24/48/72), `nudge_enabled` |
| **Gmail** | | |
| `/api/v1/gmail/status/` | GET | Is org's Gmail connected? Returns `{connected, email}` |
| `/api/v1/gmail/oauth/start/` | GET | Redirect to Google OAuth consent — accepts `?auth=<JWT>` for browser-redirect flows |
| `/api/v1/gmail/oauth/callback/` | GET | Gmail OAuth callback — stores per-org access + refresh tokens |

---

## Running Tests

```bash
# All tests (326 passing)
pytest -v --tb=short

# Unit tests + Gemini integration tests (real Vertex AI calls — needs ADC token)
pytest -v --tb=short --run-slow

# Specific app or file
pytest apps/accounts/tests/test_auth.py -v
pytest apps/commitments/ -v
pytest -k "test_risk" -v

# With coverage
pytest --cov=apps --cov=extraction --cov-report=html
```

**Integration test note:** `--run-slow` tests call real Gemini. They require `GEMINI_API_KEY` set in `.env` and take ~30–60s per test.

---

## Infrastructure

| Service | Version | Address | Managed by |
|---|---|---|---|
| PostgreSQL | 18.3 | localhost:5432 | Homebrew (auto-start) |
| Redis | 7.x | localhost:6379 | Homebrew (auto-start) |
| Database | commitment_os | no password | Homebrew peer auth |
| Gemini AI | 2.5 Flash Lite | Google AI Studio | `GEMINI_API_KEY` (production) / ADC (local fallback) |

pgvector is installed but not used until Phase 3 (conflict detection).

---

## Common Commands

```bash
# ── Backend ──────────────────────────────────────────────────
# Migrations
python manage.py makemigrations [app]
python manage.py migrate

# Django shell
python manage.py shell

# Tests
pytest -v
pytest extraction/tests/ --run-slow -v   # with real Gemini calls
pytest --cov=apps --cov=extraction --cov-report=html

# Reset DB
dropdb commitment_os && createdb commitment_os
python manage.py migrate
python manage.py createsuperuser

# Port conflicts
lsof -i :8000   # Django
lsof -i :5432   # Postgres
lsof -i :6379   # Redis

# ── Frontend ─────────────────────────────────────────────────
cd ~/Documents/Programs/Verato/frontend

npm run dev        # dev server → http://localhost:3000
npm run build      # production build
npm run lint       # ESLint
npx tsc --noEmit   # type check without building

lsof -i :3000      # check if dev server is running
```

---

## Build Progress

| Week | Feature | Status |
|---|---|---|
| 1 | Extraction engine (transcript + import) | ✓ Done |
| 2 | Django models + API skeleton | ✓ Done |
| 3 | Ingestion pipeline + prior import | ✓ Done |
| 3.5 | Knowledge graph foundation (tags, topics, person lineage) | ✓ Done |
| 4 | Commitment actions + dashboard API | ✓ Done |
| 5 | Risk scoring + status automation (24h Celery Beat) | ✓ Done |
| 6 | Slack nudges + weekly digest email | ✓ Done |
| 6.5 | Self-serve sign-up, team invites, per-org Slack OAuth | ✓ Done |
| 7 | API gap-fill — bulk-confirm, nudge, tag autocomplete, org settings, Slack status | ✓ Done |
| F1 | Frontend scaffold — design system, auth pages, shared components | ✓ Done |
| F2 | Onboarding wizard — Slack connect, import, done screens | ✓ Done |
| F3 | Dashboard — stat cards, filters, commitment list | ✓ Done |
| F4 | Commitment detail — edit, actions, resolve, nudge, tag editor | ✓ Done |
| F5 | Upload + extraction review — polling, bulk confirm, per-row review | ✓ Done |
| F6 | Meetings list, People list, Settings (Org / Slack / Team) | ✓ Done |
| W8 | API hardening — audit log, person CRUD/merge, meeting PATCH, participant mgmt, reopen, logout | ✓ Done |
| W9 | Production fixes — Slack OAuth JWT flow, `GET /auth/me/`, Gemini API key, upload file merge, Django admin pipeline dashboard | ✓ Done |
| W10 | Nudge engine — configurable Slack nudge schedule, NudgeLog, CoS escalation, per-org enable/disable | ✓ Done |
| W11 | Slack user management — workspace search, import, full sync; manual nudge queue flags on CommitmentSerializer | ✓ Done |
| W12 | Gmail OAuth — send nudge emails from org's Gmail, poll reply threads, Gemini intent parsing, GmailPollLog | ✓ Done |
| W12.5 | Admin configurability — per-org Gmail polling enable/disable + frequency (15/30/60/120 min); prompts stored in DB | ✓ Done |
| — | Frontend Gmail/nudge settings UI | Next |

```
PHASE 1 — Local backend (Weeks 1–7)           ← COMPLETE
PHASE 2 — Frontend (Next.js, Weeks F1–F6)     ← COMPLETE (running on Cloud Run)
PHASE 2.5 — Production hardening              ← COMPLETE (live at api.verato.twocents.ai)
PHASE 2.6 — Nudge engine + Gmail OAuth        ← COMPLETE
PHASE 3 — Frontend nudge/Gmail settings UI    ← Next
```

---

## Environment Variables

### Backend — `backend/.env` (gitignored — never commit)

| Variable | When needed | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | Always | Set |
| `DB_*` | Always | Set — no password, Homebrew auth |
| `REDIS_URL` | Always | Set — `redis://localhost:6379/0` |
| `GEMINI_API_KEY` | Week 1+ | Google AI Studio API key — used in production and local dev |
| `GOOGLE_CLOUD_PROJECT` | Optional | Only needed if using Vertex AI ADC as a local fallback |
| `GOOGLE_CLOUD_LOCATION` | Optional | Only needed if using Vertex AI ADC as a local fallback |
| `GEMINI_EXTRACTION_MODEL` | Week 1+ | Set — `gemini-2.5-flash-lite` |
| `APP_BASE_URL` | Week 6.5+ | Frontend URL for invite links (default: `http://localhost:3000`) |
| `SLACK_BOT_TOKEN` | Week 6+ | Global fallback bot token (per-org token overrides via OAuth) |
| `SLACK_SIGNING_SECRET` | Week 6+ | Verifies Slack action webhooks |
| `SLACK_CLIENT_ID` | Week 6.5+ | Slack OAuth app credentials |
| `SLACK_CLIENT_SECRET` | Week 6.5+ | Slack OAuth app credentials |
| `SLACK_OAUTH_REDIRECT_URI` | Week 6.5+ | Default: `http://localhost:8000/api/v1/slack/oauth/callback/` |
| `SENDGRID_API_KEY` | Week 6+ | Weekly digest email (Gmail OAuth used for nudge emails) |
| `DEFAULT_FROM_EMAIL` | Week 6+ | Set — `noreply@verato.app` |
| `GOOGLE_CLIENT_ID` | W12+ | Google Cloud Console OAuth 2.0 client — for Gmail OAuth |
| `GOOGLE_CLIENT_SECRET` | W12+ | Google Cloud Console OAuth 2.0 client secret |
| `GOOGLE_GMAIL_REDIRECT_URI` | W12+ | Default: `http://localhost:8000/api/v1/gmail/oauth/callback/` |

**`GEMINI_API_KEY`** — required for production. Get it from [aistudio.google.com](https://aistudio.google.com). Local dev falls back to Vertex AI ADC if the key is absent.

### Frontend — `frontend/.env.local` (gitignored — never commit)

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | Django API base URL — defaults to `http://localhost:8000/api/v1` if unset |
