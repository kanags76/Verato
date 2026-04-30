# Verato

Accountability layer for organisations. Extracts every commitment made in meetings, assigns it an owner, scores risk, and nudges before it slips.

**Stack:** Django REST API · PostgreSQL 18 · Redis · Celery · Vertex AI (Gemini)
**Repo:** https://github.com/kanags76/Verato (private)

---

## Project Structure

```
Verato/
├── backend/                   Django project
│   ├── apps/
│   │   ├── accounts/          Users, Organisations, Persons
│   │   ├── meetings/          Meeting ingestion + transcripts
│   │   ├── commitments/       Core entity — track, escalate, resolve
│   │   ├── notifications/     Slack nudges, weekly email digest
│   │   └── analytics/         Phase 2 — delivery rates, risk trends
│   ├── extraction/            AI extraction engine (pure Python, no Django dependency)
│   │   ├── extractor.py       extract_commitments() — transcript → JSON
│   │   ├── importer.py        extract_from_document() — prior tracker → JSON
│   │   ├── prompt_builder.py  Gemini prompts for transcript + import
│   │   ├── parser.py          safe_json_parse() — strips fences, validates
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
└── AI Build Prompt/           Planning docs
```

---

## Local Dev — Start of Session

```bash
# 1. Verify services (auto-start on login, but always confirm)
brew services list | grep -E "postgresql|redis"
pg_isready        # → localhost:5432 - accepting connections
redis-cli ping    # → PONG

# 2. Restart if stopped
brew services start postgresql@18
brew services start redis

# 3. Navigate to project + activate venv
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# 4. (If Vertex AI ADC token has expired — do once, valid ~1 hour)
gcloud auth application-default login
```

### Four terminal tabs

```
Tab 1 — Django API       python manage.py runserver
Tab 2 — Celery worker    celery -A config worker --loglevel=info
Tab 3 — Tests            pytest -v --tb=short
Tab 4 — Git / shell      free
```

### End of session

```bash
# Stop Django  → Ctrl+C in Tab 1
# Stop Celery  → Ctrl+C in Tab 2
# Services stay running, or stop them:
brew services stop postgresql@18
brew services stop redis
```

---

## Localhost URLs

| URL | What it is |
|---|---|
| `http://localhost:8000/api/health/` | Health check → `{"status": "ok"}` |
| `http://localhost:8000/admin/` | Django admin (admin / admin1234) |
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — main API test interface** |
| `http://localhost:8000/api/schema/redoc/` | ReDoc — clean API docs |
| `http://localhost:8000/api/schema/` | Raw OpenAPI JSON |
| `http://localhost:8000/__debug__/` | Django debug toolbar (local only) |

---

## API Endpoints

### Authenticating in Swagger UI

```
1. POST /api/v1/auth/token/ → {"username": "admin", "password": "admin1234"}
2. Copy the "access" value
3. Click Authorize (top right) → enter: Bearer <token>
4. All subsequent calls are authenticated
```

### Full MVP API Surface

| Endpoint | Method | Week | Description |
|---|---|---|---|
| `/api/v1/auth/token/` | POST | 2 | Get JWT access + refresh token |
| `/api/v1/auth/token/refresh/` | POST | 2 | Refresh JWT |
| `/api/v1/auth/token/blacklist/` | POST | 2 | Logout |
| `/api/v1/dashboard/` | GET | 4 | `{overdue, at_risk, on_track, total_active}` |
| `/api/v1/meetings/` | GET | 2 | List org meetings |
| `/api/v1/meetings/upload/` | POST | 3 | Upload transcript → 202 + meeting_id |
| `/api/v1/meetings/{id}/status/` | GET | 3 | Poll processing status |
| `/api/v1/meetings/import/` | POST | 3 | Upload prior tracker doc → 202 + import_id |
| `/api/v1/meetings/import/{id}/status/` | GET | 3 | Poll import status |
| `/api/v1/meetings/zoom/webhook/` | POST | 6 | Zoom auto-ingest (stretch) |
| `/api/v1/commitments/` | GET | 2 | List with filters: `?status=` `?owner=` `?source=` `?risk_gte=` |
| `/api/v1/commitments/{id}/` | GET, PATCH | 2 | Detail + history / update owner+deadline |
| `/api/v1/commitments/{id}/confirm/` | POST | 4 | PENDING_REVIEW → ACTIVE |
| `/api/v1/commitments/{id}/reject/` | POST | 4 | Discard + log feedback signal |
| `/api/v1/commitments/{id}/escalate/` | POST | 4 | → ESCALATED + EscalationEvent |
| `/api/v1/commitments/{id}/resolve/` | POST | 4 | `{outcome, note, new_deadline?}` |
| `/api/v1/persons/` | GET | 2 | Org participants (for owner picker) |
| `/api/v1/persons/{id}/` | GET | 2 | Person detail + delivery rate |

---

## Running Tests

```bash
# Unit tests (fast — no API calls, no DB required)
pytest -v --tb=short

# Unit tests + Gemini integration tests (real Vertex AI calls — needs ADC token)
pytest -v --tb=short --run-slow

# Specific test file
pytest extraction/tests/test_parser.py -v

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

pgvector is installed but not used until Phase 2 (conflict detection).

---

## Common Commands

```bash
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
```

---

## Build Progress

| Week | Feature | Branch | Status |
|---|---|---|---|
| 1 | Extraction engine (transcript + import) | `feature/week1-extraction-engine` | ✓ Done |
| 2 | Django models + API skeleton | `feature/week2-models-api` | ⏳ Next |
| 3 | Ingestion pipeline + prior import | `feature/week3-ingestion` | — |
| 4 | Commitment actions + dashboard API | `feature/week4-commitment-actions` | — |
| 5 | Risk scoring + status automation | `feature/week5-risk-scoring` | — |
| 6 | Slack nudges + weekly digest email | `feature/week6-notifications` | — |

```
PHASE 1 — Local backend (Weeks 1–6)       ← Week 1 complete
PHASE 2 — Deploy to AWS ECS               (after Week 6)
PHASE 3 — Frontend on GCP Cloud Run       (after Phase 2)
```

---

## Environment Variables

All in `backend/.env` (gitignored — never commit).

| Variable | When needed | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | Always | Set |
| `DB_*` | Always | Set — no password, Homebrew auth |
| `REDIS_URL` | Always | Set — `redis://localhost:6379/0` |
| `GOOGLE_CLOUD_PROJECT` | Week 1+ | Set — `verato` |
| `GOOGLE_CLOUD_LOCATION` | Week 1+ | Set — `us-central1` |
| `GEMINI_EXTRACTION_MODEL` | Week 1+ | Set — `gemini-2.5-flash-lite` |
| `SLACK_BOT_TOKEN` | Week 6 | Placeholder |
| `SENDGRID_API_KEY` | Week 6 | Placeholder |
| `ZOOM_*` | Week 6 (stretch) | Placeholder |
| AWS credentials | Phase 2 | Placeholder |

**No `GEMINI_API_KEY`** — Vertex AI uses Application Default Credentials (ADC), not an API key. Run `gcloud auth application-default login` to authenticate.
