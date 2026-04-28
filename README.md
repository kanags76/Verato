# Commitment OS

Accountability layer for organisations. Extracts every commitment made in meetings, tracks it, detects conflicts, and surfaces risk.

**Stack:** Django REST API · PostgreSQL 18 + pgvector · Redis · Celery · Swagger UI
**Repo:** https://github.com/kanags76/Verato (private)

---

## Project Structure

```
Verato/
├── backend/                   Django project
│   ├── apps/
│   │   ├── accounts/          Users, Organisations
│   │   ├── meetings/          Meeting ingestion + transcripts
│   │   ├── commitments/       Core entity — track, escalate, resolve
│   │   ├── notifications/     Slack nudges, email digest
│   │   └── analytics/         Delivery rates, risk trends
│   ├── extraction/            AI extraction engine (pure Python)
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

# 3. Activate venv + start Django
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver
```

### Four terminal tabs

```
Tab 1 — Django API       python manage.py runserver
Tab 2 — Celery worker    celery -A config worker --loglevel=info
Tab 3 — Tests            pytest -v --tb=short
Tab 4 — Git / shell      free
```

---

## Localhost URLs

### Core

| URL | What it is |
|---|---|
| `http://localhost:8000/api/health/` | Health check → `{"status": "ok"}` |
| `http://localhost:8000/admin/` | Django admin (admin / admin1234) |
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — main API test interface** |
| `http://localhost:8000/api/schema/redoc/` | ReDoc — clean API docs |
| `http://localhost:8000/api/schema/` | Raw OpenAPI JSON |
| `http://localhost:8000/__debug__/` | Django debug toolbar (local only) |

### API v1 Endpoints (built week by week)

| URL | Method | Week | Description |
|---|---|---|---|
| `/api/v1/auth/token/` | POST | 2 | Get JWT access + refresh token |
| `/api/v1/auth/token/refresh/` | POST | 2 | Refresh JWT token |
| `/api/v1/dashboard/` | GET | 4 | Aggregated stats for CoS |
| `/api/v1/meetings/` | GET, POST | 2 | List / create meetings |
| `/api/v1/meetings/{id}/` | GET, PATCH | 2 | Meeting detail |
| `/api/v1/meetings/upload/` | POST | 3 | Upload transcript → triggers extraction |
| `/api/v1/meetings/{id}/status/` | GET | 3 | Poll async processing status |
| `/api/v1/commitments/` | GET, POST | 2 | List / create commitments |
| `/api/v1/commitments/{id}/` | GET, PATCH | 2 | Commitment detail |
| `/api/v1/commitments/{id}/confirm/` | POST | 4 | PENDING → ACTIVE |
| `/api/v1/commitments/{id}/escalate/` | POST | 4 | Trigger escalation |
| `/api/v1/commitments/{id}/resolve/` | POST | 4 | Mark delivered / deferred / cancelled |
| `/api/v1/conflicts/` | GET | 9 | List unresolved conflicts |
| `/api/v1/conflicts/{id}/resolve/` | POST | 9 | Mark conflict resolved |
| `/api/v1/persons/` | GET | 4 | Org participants + delivery stats |
| `/api/v1/analytics/delivery-rates/` | GET | 7 | Delivery rates by person / team |
| `/api/v1/analytics/risk-summary/` | GET | 7 | Risk distribution snapshot |
| `/api/v1/analytics/commitment-volume/` | GET | 7 | Commits over time |

### Authenticating in Swagger UI

```
1. POST /api/v1/auth/token/ → {"username": "admin", "password": "admin1234"}
2. Copy the "access" value
3. Click Authorize (top right) → enter: Bearer <token>
4. All subsequent calls are authenticated
```

---

## Infrastructure

| Service | Version | Address | Auto-starts |
|---|---|---|---|
| PostgreSQL | 18.3 (Homebrew) | localhost:5432 | Yes |
| pgvector | 0.8.2 | — | — |
| Redis | 7.x (Homebrew) | localhost:6379 | Yes |
| Database | commitment_os | No password (Homebrew auth) | — |

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
pytest apps/commitments/ -v
pytest --cov=apps --cov-report=html

# Reset DB (nuclear)
dropdb commitment_os && createdb commitment_os
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
python manage.py migrate
python manage.py createsuperuser

# Port conflicts
lsof -i :8000   # Django
lsof -i :5432   # Postgres
lsof -i :6379   # Redis
```

---

## Build Phases

```
PHASE 1 — Local backend (Weeks 1–9)     ← you are here
PHASE 2 — Deploy to AWS ECS             (after Week 9)
PHASE 3 — Frontend on GCP Cloud Run     (after Phase 2)
```

See `AI Build Prompt/02 - 04_build_plan.md` for the full week-by-week plan.

---

## Environment Variables

Copy `.env.example` → `.env` and fill in values as you reach each week.

| Variable | When needed |
|---|---|
| `GEMINI_API_KEY` | Week 1 — get from aistudio.google.com |
| `SLACK_BOT_TOKEN` | Week 6 |
| `SENDGRID_API_KEY` | Week 8 |
| `ZOOM_*` | Week 9 |
| AWS credentials | Phase 2 |
| GCP credentials | Phase 3 |
