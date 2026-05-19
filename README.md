# Verato

Accountability layer for organisations. Extracts every commitment made in meetings, assigns it an owner, scores risk, and nudges before it slips.

**Stack:** Django REST API · Next.js 16 · PostgreSQL 18 · Redis · Celery · Vertex AI (Gemini)
**Repo:** https://github.com/kanags76/Verato (private)

---

## Project Structure

```
Verato/
├── backend/                   Django project
│   ├── apps/
│   │   ├── accounts/          Organisation (plan), User (is_org_admin), Person, Invitation
│   │   ├── meetings/          Meeting (meeting_type, summary), MeetingParticipant, MeetingTopic
│   │   ├── commitments/       Commitment, CommitmentTag (M2M, org-scoped), EscalationEvent, risk.py
│   │   ├── notifications/     Slack nudges, weekly email digest, NudgeLog, Slack OAuth
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

### Step 2 — (If Vertex AI ADC token has expired — once per day, ~1 hour TTL)

```bash
gcloud auth application-default login
```

### Step 3 — Open five terminal tabs and run one command in each

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
| `/api/v1/auth/token/blacklist/` | POST | Logout |
| **Org** | | |
| `/api/v1/orgs/` | GET | List orgs accessible to current user |
| `/api/v1/orgs/{id}/settings/` | PATCH | Update org settings: `confidence_threshold`, `nudge_hours_before`, `digest_day`, `digest_hour` |
| **Dashboard** | | |
| `/api/v1/dashboard/` | GET | `{overdue, at_risk, on_track, total_active}` |
| **Meetings** | | |
| `/api/v1/meetings/` | GET | List org meetings (includes `commitment_count`, `pending_count`) |
| `/api/v1/meetings/upload/` | POST | Upload transcript text or file → 202 + meeting_id |
| `/api/v1/meetings/import/` | POST | Upload prior tracker doc → 202 + meeting_id |
| `/api/v1/meetings/{id}/` | GET | Meeting detail |
| `/api/v1/meetings/{id}/status/` | GET | Poll processing status |
| `/api/v1/meetings/zoom/webhook/` | POST | Zoom auto-ingest (stretch) |
| **Commitments** | | |
| `/api/v1/commitments/` | GET | List with filters: `?status=` `?owner=` `?priority=` `?source=` `?tags__label=` `?deadline_before=` `?risk_gte=` `?meeting=` |
| `/api/v1/commitments/{id}/` | GET, PATCH | Detail (includes `tags[]`, `escalations[]`) / update owner, deadline, tags, priority |
| `/api/v1/commitments/bulk-confirm/` | POST | Confirm all PENDING_REVIEW; optional `{meeting?, min_confidence?}` |
| `/api/v1/commitments/{id}/confirm/` | POST | PENDING_REVIEW → ACTIVE |
| `/api/v1/commitments/{id}/reject/` | POST | → CANCELLED + logs ExtractionFeedback |
| `/api/v1/commitments/{id}/escalate/` | POST | → ESCALATED + EscalationEvent; accepts `{message}` |
| `/api/v1/commitments/{id}/resolve/` | POST | `{outcome: delivered\|deferred\|cancelled, note?, new_deadline?}` |
| `/api/v1/commitments/{id}/nudge/` | POST | Send Slack deadline nudge to the commitment owner right now |
| **Tags** | | |
| `/api/v1/tags/` | GET | Tag autocomplete ranked by usage; `?q=` for prefix filter |
| **Persons** | | |
| `/api/v1/persons/` | GET | List org participants |
| `/api/v1/persons/{id}/` | GET | Person detail + delivery stats + meeting lineage |
| `/api/v1/persons/{id}/timeline/` | GET | Chronological meeting history with commitments + topics |
| `/api/v1/persons/{id}/topics/` | GET | Topic frequency list `[{label, count, last_seen}]` |
| `/api/v1/persons/{id}/link-slack/` | POST | Link Slack user ID to this person |
| **Slack** | | |
| `/api/v1/slack/status/` | GET | Is org's Slack connected? Returns `{connected, workspace_id, workspace_name}` |
| `/api/v1/slack/test-message/` | POST | Send a test DM to the requesting user's linked Slack account |
| `/api/v1/slack/actions/` | POST | Slack interactive button handler (Done/Delayed/Blocked) |
| `/api/v1/slack/oauth/start/` | GET | Redirect to Slack OAuth consent (authenticated users only) |
| `/api/v1/slack/oauth/callback/` | GET | Slack OAuth callback — stores per-org bot token |

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

**Integration test note:** `--run-slow` tests call real Vertex AI Gemini. They require a valid ADC token (`gcloud auth application-default login`) and take ~30–60s per test.

---

## Infrastructure

| Service | Version | Address | Managed by |
|---|---|---|---|
| PostgreSQL | 18.3 | localhost:5432 | Homebrew (auto-start) |
| Redis | 7.x | localhost:6379 | Homebrew (auto-start) |
| Database | commitment_os | no password | Homebrew peer auth |
| Vertex AI | Gemini 2.5 Flash Lite | GCP us-central1 | ADC (gcloud auth) |

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
| F7 | Mobile polish, E2E tests, Vercel deploy | Next |
| — | AWS deployment (Phase 3) | After deploy |

```
PHASE 1 — Local backend (Weeks 1–7)           ← COMPLETE (326 tests passing)
PHASE 2 — Frontend (Next.js, Weeks F1–F6)     ← COMPLETE (running on localhost:3000)
           Week F7 — polish + deploy           ← Next  →  see 06_phase2_frontend_build_plan.md
PHASE 3 — Deploy to AWS ECS                   (after frontend deploy)
```

---

## Environment Variables

### Backend — `backend/.env` (gitignored — never commit)

| Variable | When needed | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | Always | Set |
| `DB_*` | Always | Set — no password, Homebrew auth |
| `REDIS_URL` | Always | Set — `redis://localhost:6379/0` |
| `GOOGLE_CLOUD_PROJECT` | Week 1+ | Set — `verato` |
| `GOOGLE_CLOUD_LOCATION` | Week 1+ | Set — `us-central1` |
| `GEMINI_EXTRACTION_MODEL` | Week 1+ | Set — `gemini-2.5-flash-lite` |
| `APP_BASE_URL` | Week 6.5+ | Frontend URL for invite links (default: `http://localhost:3000`) |
| `SLACK_BOT_TOKEN` | Week 6+ | Global fallback bot token (per-org token overrides via OAuth) |
| `SLACK_SIGNING_SECRET` | Week 6+ | Verifies Slack action webhooks |
| `SLACK_CLIENT_ID` | Week 6.5+ | Slack OAuth app credentials |
| `SLACK_CLIENT_SECRET` | Week 6.5+ | Slack OAuth app credentials |
| `SLACK_OAUTH_REDIRECT_URI` | Week 6.5+ | Default: `http://localhost:8000/api/v1/slack/oauth/callback/` |
| `SENDGRID_API_KEY` | Week 6+ | Weekly digest email |
| `DEFAULT_FROM_EMAIL` | Week 6+ | Set — `noreply@verato.app` |
| `ZOOM_*` | Stretch | Placeholder |
| AWS credentials | Phase 3 | Placeholder |

**No `GEMINI_API_KEY`** — Vertex AI uses Application Default Credentials (ADC), not an API key. Run `gcloud auth application-default login` to authenticate.

### Frontend — `frontend/.env.local` (gitignored — never commit)

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | Django API base URL — defaults to `http://localhost:8000/api/v1` if unset |
