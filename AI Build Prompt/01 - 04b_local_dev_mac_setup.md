# Commitment OS — Mac (Apple Silicon) Local Dev Setup
## Updated: No Docker required · Homebrew-native services

> This replaces the Docker Compose section in the main build plan.
> Everything runs natively on your Mac. Faster, lighter, simpler.

---

## Your development sequence (confirmed)

```
PHASE 1 — Local backend development (Weeks 1–12)
  Mac M-series
  ├── PostgreSQL 16     (Homebrew — native ARM64)
  ├── Redis 7           (Homebrew — native ARM64)
  ├── Django 5.x        (Python venv — runs directly)
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

## Option A — Homebrew (recommended for Apple Silicon)

No Docker. Postgres and Redis run as native Mac services.
Faster startup, lower memory, no Docker Desktop overhead.

### Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Apple Silicon — add to PATH (add to ~/.zshrc)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# Verify
brew --version
```

### Install PostgreSQL 16 with pgvector

```bash
# Install Postgres 16
brew install postgresql@16

# Add to PATH (Apple Silicon path)
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Start Postgres as a background service (auto-starts on login)
brew services start postgresql@16

# Verify it's running
brew services list | grep postgresql
pg_isready   # Should show: localhost:5432 - accepting connections

# Create the database
createdb commitment_os

# Verify
psql commitment_os -c "SELECT version();"

# Install pgvector extension
brew install pgvector

# Enable pgvector in the database (run once)
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql commitment_os -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
# Should return: vector
```

### Install Redis

```bash
brew install redis

# Start Redis as a background service
brew services start redis

# Verify
brew services list | grep redis
redis-cli ping   # Should return: PONG
```

### Service management commands

```bash
# Start all services
brew services start postgresql@16
brew services start redis

# Stop all services
brew services stop postgresql@16
brew services stop redis

# Restart
brew services restart postgresql@16
brew services restart redis

# Check status
brew services list

# View Postgres logs if something goes wrong
tail -f /opt/homebrew/var/log/postgresql@16.log
```

### Update .env for Homebrew (no password needed locally)

```bash
# Homebrew Postgres uses your Mac username, no password
# Update backend/.env:

DB_NAME=commitment_os
DB_USER=     # Leave blank — uses your Mac username automatically
DB_PASSWORD= # Leave blank — no password in local Homebrew Postgres
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
```

Update `config/settings/base.py` to handle blank password:

```python
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='commitment_os'),
        'USER':     config('DB_USER',     default=''),  # blank = Mac username
        'PASSWORD': config('DB_PASSWORD', default=''),  # blank = no password
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}
```

---

## Option B — Docker Desktop (if you prefer containers)

Use this if you want your local environment to mirror production exactly,
or if you already have Docker Desktop installed and are comfortable with it.

### Install Docker Desktop for Apple Silicon

```bash
# Download from https://www.docker.com/products/docker-desktop/
# Choose: Mac with Apple Chip
# Install, open Docker Desktop, wait for it to start

# Verify
docker --version
docker-compose --version
```

### docker-compose.yml (Postgres + Redis only)

```yaml
# backend/docker-compose.yml
# Only runs the infrastructure services.
# Django and Celery still run natively in your terminal.

version: '3.9'

services:
  db:
    image: pgvector/pgvector:pg16
    # This image has native ARM64 support — works on Apple Silicon
    platform: linux/arm64
    container_name: commitment_os_db
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
    platform: linux/arm64
    container_name: commitment_os_redis
    ports:
      - "6379:6379"

volumes:
  postgres_data:
    name: commitment_os_postgres_data
```

```bash
# Start services
docker-compose up db redis -d

# Enable pgvector (run once after first start)
docker-compose exec db psql -U postgres -d commitment_os \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Stop services
docker-compose down

# Stop and delete all data (nuclear reset)
docker-compose down -v
```

---

## Recommendation for you (Apple Silicon, solo founder)

**Use Homebrew (Option A).** Here's why:

| Factor | Homebrew | Docker |
|---|---|---|
| Memory overhead | ~50MB | ~3-4GB for Docker Desktop |
| Startup time | Already running (auto-start) | 30-60 seconds |
| Apple Silicon support | Native ARM64 binary | Emulation layer for some images |
| Complexity | Two brew commands | docker-compose + daemon running |
| Mirrors production | No (but doesn't need to) | Closer to prod |
| pgvector support | Yes (brew install pgvector) | Yes |

The "mirrors production" argument for Docker only matters when you have a team
where environment differences cause bugs. Solo founder on Mac → just use Homebrew.
When you Dockerise for AWS ECS deployment, that's a separate Dockerfile for production.
Your local env doesn't need to match it.

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
- This is your main tool for all backend development

### 2. REST Client in VS Code (secondary — for saved test scenarios)

Create `backend/api-tests/` folder with `.http` files.
VS Code REST Client extension runs them inline.

```
# backend/api-tests/auth.http

### Get JWT token
POST http://localhost:8000/api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "yourpassword"
}

### -----------------------------------------------

### Get dashboard (paste token from above response)
GET http://localhost:8000/api/v1/dashboard/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhb...
```

```
# backend/api-tests/commitments.http

@token = eyJ0eXAiOiJKV1QiLCJhb...  # set this once

### List all commitments
GET http://localhost:8000/api/v1/commitments/
Authorization: Bearer {{token}}

### List at-risk only
GET http://localhost:8000/api/v1/commitments/?status=at_risk
Authorization: Bearer {{token}}

### Upload a transcript
POST http://localhost:8000/api/v1/meetings/upload/
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "title": "Q2 Planning",
  "transcript_text": "Sarah: I'll have the pricing deck ready by Thursday. Tom: I'll send the hiring brief to HR by end of week.",
  "occurred_at": "2026-04-22T14:00:00Z"
}

### Confirm a commitment
POST http://localhost:8000/api/v1/commitments/COMMITMENT-UUID-HERE/confirm/
Authorization: Bearer {{token}}
```

### 3. Django Admin (for data inspection)

`http://localhost:8000/admin/`

- Browse all database records directly
- Useful for verifying extraction results
- No code needed — register models in `admin.py` per app

---

## Complete local dev terminal layout

Four terminal tabs in VS Code (`Ctrl+Shift+\`` `):

```
Tab 1 — Django API
  cd ~/projects/commitment-os/backend
  source .venv/bin/activate
  export DJANGO_SETTINGS_MODULE=config.settings.local
  python manage.py runserver
  → http://localhost:8000

Tab 2 — Celery worker (only open when testing async tasks)
  cd ~/projects/commitment-os/backend
  source .venv/bin/activate
  export DJANGO_SETTINGS_MODULE=config.settings.local
  celery -A config worker --loglevel=info

Tab 3 — Tests (run as needed)
  cd ~/projects/commitment-os/backend
  source .venv/bin/activate
  pytest -v

Tab 4 — Free for git, migrations, shell commands
  cd ~/projects/commitment-os/backend
  source .venv/bin/activate
```

No Next.js tab needed until Phase 3.
Homebrew services (Postgres + Redis) start automatically on login — no terminal needed.

---

## Phase 2 — When to Dockerise (AWS ECS)

When your local backend is complete and tested (end of Week 12),
you create a Dockerfile for production deployment only.
This is separate from your local setup.

```dockerfile
# backend/Dockerfile  (created at Week 12, not before)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3"]

EXPOSE 8000
```

You only write this when you're ready to push to AWS.
Until then, run Django directly with `python manage.py runserver`.

---

## Phase 3 — Frontend on Google AI Studio

When the backend APIs are deployed and working on AWS ECS:

1. Open Google AI Studio (https://aistudio.google.com)
2. Use Claude or Gemini to scaffold the Next.js app
3. Point `NEXT_PUBLIC_API_URL` at your AWS ALB domain
4. Test locally against the real AWS API
5. Deploy to GCP Cloud Run

You never need to run the frontend locally against a local backend.
By Phase 3, the AWS backend is the source of truth.

---

## Quick reference — all startup commands

```bash
# Check services are running (Homebrew)
brew services list
pg_isready        # Postgres
redis-cli ping    # Redis → PONG

# Start if not running
brew services start postgresql@16
brew services start redis

# Django
cd ~/projects/commitment-os/backend
source .venv/bin/activate
python manage.py runserver

# Celery (separate tab, only when needed)
celery -A config worker --loglevel=info

# Test Gemini
bash scripts/test_gemini.sh

# Run all tests
pytest

# Django admin shell
python manage.py shell

# Reset local DB (if something goes wrong)
dropdb commitment_os
createdb commitment_os
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
python manage.py migrate
python manage.py createsuperuser
```

---

*Feed this to Claude Code in VS Code alongside the main build plan.
This document overrides the Docker Compose section in 04_build_plan.md.*
