# Commitment OS — Mac (Apple Silicon) Local Dev Setup
## Updated: No Docker required · Homebrew-native services

> This replaces the Docker Compose section in the main build plan.
> Everything runs natively on your Mac. Faster, lighter, simpler.

---

## ENVIRONMENT STATUS — What's Actually Installed

| Component | Version | Status |
|---|---|---|
| PostgreSQL | 18.3 (Homebrew) | Running, auto-starts on login |
| pgvector | 0.8.2 | Installed + enabled in commitment_os |
| Redis | 7.x (Homebrew) | Running, auto-starts on login |
| Python venv | 3.x | At `backend/.venv` |
| Django | 6.0.4 | Installed |
| Django REST Framework | 3.17.1 | Installed |
| Celery | 5.6.3 | Installed |
| drf-spectacular | 0.29.0 | Installed (Swagger UI) |
| psycopg2-binary | 2.9.12 | Installed |
| python-decouple | 3.8 | Installed |
| django-celery-results | 2.6.0 | Installed |

**Project path:** `~/Documents/Programs/Verato/backend`
**GitHub repo:** https://github.com/kanags76/Verato (private)
**Database:** `commitment_os` on localhost:5432 (no password — Homebrew auth)

---

## START OF SESSION — Run these before every coding session

```bash
# 1. Check services are up (they auto-start, but verify)
brew services list | grep -E "postgresql|redis"
pg_isready            # Should show: localhost:5432 - accepting connections
redis-cli ping        # Should return: PONG

# 2. If either service is stopped, restart it
brew services start postgresql@18
brew services start redis

# 3. Activate your Python venv
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate

# 4. Set Django settings
export DJANGO_SETTINGS_MODULE=config.settings.local

# 5. Start Django dev server
python manage.py runserver
# → http://localhost:8000
# → Swagger UI: http://localhost:8000/api/schema/ui/
```

> PostgreSQL and Redis auto-start on Mac login via Homebrew.
> You usually only need steps 3–5 at the start of each session.

---

## STOP SESSION — Shut everything down cleanly

```bash
# Stop Django (Ctrl+C in the terminal running it)

# Stop Celery (Ctrl+C in the terminal running it)

# Stop services (optional — they're lightweight, leaving them running is fine)
brew services stop postgresql@18
brew services stop redis
```

---

## Your development sequence (confirmed)

```
PHASE 1 — Local backend development (Weeks 1–12)
  Mac M-series
  ├── PostgreSQL 18     (Homebrew — native ARM64) ✓ DONE
  ├── Redis 7           (Homebrew — native ARM64) ✓ DONE
  ├── Django 6.x        (Python venv — runs directly) ✓ DONE
  ├── Celery worker     (Python venv — runs directly)
  └── Swagger UI        (auto-generated — your "dummy screen" for API testing)

PHASE 2 — Deploy backend to AWS
  Dockerise Django for ECS
  RDS PostgreSQL (pgvector enabled)
  ElastiCache Redis
  Verify all APIs work in cloud

PHASE 3 — Build and deploy frontend
  Google AI Studio → build Next.js frontend
  Deploy to GCP Cloud Run
  Point NEXT_PUBLIC_API_URL at AWS backend
```

You do NOT need a frontend locally at all during Phase 1.
Swagger UI is your interactive API tester for every endpoint.

---

## What was set up (completed steps)

### PostgreSQL 18

```bash
brew install postgresql@18
echo 'export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
brew services start postgresql@18
createdb commitment_os
```

### pgvector

```bash
brew install pgvector
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
# Verified: returns 'vector'
```

### Redis

```bash
brew install redis
brew services start redis
redis-cli ping   # PONG ✓
```

### Python venv + dependencies

```bash
cd ~/Documents/Programs/Verato/backend
python3 -m venv .venv
source .venv/bin/activate
pip install django djangorestframework psycopg2-binary celery redis \
    python-decouple drf-spectacular django-celery-results
pip freeze > requirements.txt
```

### .env (Homebrew — no password needed)

```
DB_NAME=commitment_os
DB_USER=             # blank = uses your Mac username (kanags)
DB_PASSWORD=         # blank = no password for local Homebrew Postgres
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
```

### config/settings/base.py

```python
from decouple import config

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='commitment_os'),
        'USER':     config('DB_USER',     default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
```

### GitHub

```bash
gh repo create kanags76/Verato --private --source . --remote origin --push
# Repo: https://github.com/kanags76/Verato
```

---

## Service management commands

```bash
# Start all services
brew services start postgresql@18
brew services start redis

# Stop all services
brew services stop postgresql@18
brew services stop redis

# Restart
brew services restart postgresql@18
brew services restart redis

# Check status
brew services list

# View Postgres logs if something goes wrong
tail -f /opt/homebrew/var/log/postgresql@18.log
```

---

## Complete local dev terminal layout

Four terminal tabs in VS Code:

```
Tab 1 — Django API
  cd ~/Documents/Programs/Verato/backend
  source .venv/bin/activate
  export DJANGO_SETTINGS_MODULE=config.settings.local
  python manage.py runserver
  → http://localhost:8000

Tab 2 — Celery worker (only open when testing async tasks)
  cd ~/Documents/Programs/Verato/backend
  source .venv/bin/activate
  export DJANGO_SETTINGS_MODULE=config.settings.local
  celery -A config worker --loglevel=info

Tab 3 — Tests (run as needed)
  cd ~/Documents/Programs/Verato/backend
  source .venv/bin/activate
  pytest -v

Tab 4 — Free for git, migrations, shell commands
  cd ~/Documents/Programs/Verato/backend
  source .venv/bin/activate
```

No Next.js tab needed until Phase 3.
Homebrew services (Postgres + Redis) start automatically on login — no terminal needed.

---

## "Dummy screens" in VS Code — what to actually use

You do not need to build any frontend screens to develop and test the backend.
Use these instead:

### 1. Swagger UI (primary — best for API testing)

Auto-generated by drf-spectacular. Zero setup. Available at:
`http://localhost:8000/api/schema/ui/`

- Lists every endpoint
- Shows request/response schemas
- Execute any request directly in the browser
- Handles JWT auth (click Authorize → paste your token)

### 2. REST Client in VS Code (secondary — for saved test scenarios)

Create `backend/api-tests/` folder with `.http` files.

```
# backend/api-tests/auth.http

### Get JWT token
POST http://localhost:8000/api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "yourpassword"
}

### Get dashboard
GET http://localhost:8000/api/v1/dashboard/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhb...
```

### 3. Django Admin (for data inspection)

`http://localhost:8000/admin/`

---

## Reset local DB (if something goes wrong)

```bash
dropdb commitment_os
createdb commitment_os
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

---

## Phase 2 — When to Dockerise (AWS ECS)

When your local backend is complete and tested (end of Week 12),
you create a Dockerfile for production deployment only.

```dockerfile
# backend/Dockerfile  (created at Week 12, not before)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3"]

EXPOSE 8000
```

---

## Phase 3 — Frontend on Google AI Studio

When the backend APIs are deployed and working on AWS ECS:

1. Open Google AI Studio (https://aistudio.google.com)
2. Use Claude or Gemini to scaffold the Next.js app
3. Point `NEXT_PUBLIC_API_URL` at your AWS ALB domain
4. Test locally against the real AWS API
5. Deploy to GCP Cloud Run

---

*Feed this to Claude Code in VS Code alongside the main build plan.
This document overrides the Docker Compose section in 04_build_plan.md.*
