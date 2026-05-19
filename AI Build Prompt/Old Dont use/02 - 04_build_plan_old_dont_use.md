# Commitment OS — Build Plan
## Apple Silicon Mac · GitHub · Localhost First · AWS then GCP

> **Machine:** Apple Silicon Mac (M1/M2/M3)
> **Source control:** GitHub (private) — https://github.com/kanags76/Verato
> **Local dev:** Django + Celery run natively in venv · Postgres + Redis via Homebrew (no Docker)
> **API testing:** Swagger UI at localhost:8000/api/schema/ui/ (no frontend needed)
> **Deployment sequence:** Backend → AWS ECS first · Frontend → GCP Cloud Run second
> **Frontend build tool:** Google AI Studio (generates Next.js, deployed to Cloud Run)

---

## EVERY SESSION — Run these at the start of each coding session

> These are the only commands you need day-to-day once setup is complete.

```bash
# 1. Verify services are up (auto-start on login, but always confirm)
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
| 1.14 | First migration + superuser | ✓ DONE — admin/admin1234 |
| 1.15 | Gemini API verification | ⏳ TODO — add GEMINI_API_KEY to .env |
| 1.16 | GitHub Actions CI | ⏳ TODO |

---

## The Three Phases — What You're Building and When

```
PHASE 1 — LOCAL BACKEND (Weeks 1–9)
────────────────────────────────────
Django REST API running on localhost:8000
All APIs tested via Swagger UI — no frontend written yet
Celery workers running locally for async tasks
Postgres 18 + Redis via Homebrew (native ARM64, no Docker)

PHASE 2 — CLOUD BACKEND (After Week 9)
────────────────────────────────────────
Push Django backend to AWS ECS
Postgres moves to RDS, Redis to ElastiCache
Swagger UI still works — now at api.commitment-os.com/api/schema/ui/
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

### Step 1.1 — GitHub Repository ✓ DONE

Repo: https://github.com/kanags76/Verato (private)
Connected via gh CLI. Remote origin set.

---

### Step 1.2 — GitHub Auth ✓ DONE

```bash
gh auth status
# ✓ Logged in to github.com account kanags76
```

---

### Step 1.3 — Project Directory ✓ DONE

```
~/Documents/Programs/Verato/
├── AI Build Prompt/          ← planning docs
├── backend/                  ← Django project lives here
│   ├── .venv/                ← Python venv (gitignored)
│   ├── .env                  ← secrets (gitignored)
│   ├── config/
│   │   └── settings/
│   │       └── base.py       ← DB + Redis config (stub)
│   └── requirements.txt
└── .gitignore
```

---

### Step 1.4 — Branch Strategy ⏳ TODO

```bash
cd ~/Documents/Programs/Verato

# Create develop branch — all feature work merges here
git checkout -b develop
git push origin develop
# In GitHub: Settings → Branches → set develop as default branch

# Weekly feature branch pattern
git checkout develop && git pull origin develop
git checkout -b feature/week1-extraction-engine
```

```
main         production. Protected. Merge from develop only.
develop      integration. All feature branches merge here.
feature/*    one per week, e.g. feature/week1-extraction-engine
fix/*        bug fixes, e.g. fix/risk-score-null-owner
```

---

### Step 1.5 — Prerequisites ✓ DONE (Homebrew, no Docker)

```
PostgreSQL 18.3   Homebrew — native ARM64 — running, auto-starts on login
pgvector 0.8.2    Homebrew — enabled in commitment_os DB
Redis 7.x         Homebrew — native ARM64 — running, auto-starts on login
Python venv       ~/Documents/Programs/Verato/backend/.venv
Django 6.0.4      Installed in venv
All deps          Installed — see requirements.txt
```

---

### Step 1.6 — VS Code Setup ⏳ TODO

```bash
# Install extensions
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

### Step 1.7 — Homebrew Services ✓ DONE (Docker not used)

No Docker. Services run natively via Homebrew.

```bash
# Verify both are running
brew services list | grep -E "postgresql|redis"
pg_isready        # localhost:5432 - accepting connections
redis-cli ping    # PONG
```

---

### Step 1.8 — Django Project Scaffold ⏳ NEXT

Everything below runs in `~/Documents/Programs/Verato/backend` with the venv active.

```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate

# Scaffold Django project (creates manage.py, config/wsgi.py, config/urls.py, etc.)
django-admin startproject config .

# Settings package — move settings.py into a package
mkdir -p config/settings
mv config/settings.py config/settings/base.py
touch config/settings/__init__.py
touch config/settings/local.py
touch config/settings/production.py

# App directories
mkdir -p apps extraction

# Django apps (one per domain)
python manage.py startapp accounts     apps/accounts
python manage.py startapp meetings     apps/meetings
python manage.py startapp commitments  apps/commitments
python manage.py startapp notifications apps/notifications
python manage.py startapp analytics    apps/analytics

# Extraction module (pure Python — not a Django app)
touch extraction/__init__.py
touch extraction/extractor.py
touch extraction/prompt_builder.py
touch extraction/parser.py
touch extraction/conflict_detector.py
touch extraction/calibration.py
mkdir -p extraction/tests/fixtures
touch extraction/tests/__init__.py
touch extraction/tests/test_extractor.py

# pytest config
cat > pytest.ini << 'EOF'
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
python_files = tests.py test_*.py *_tests.py
markers =
    slow: LLM calls, integration tests
    unit: no DB, no network
EOF
```

---

### Step 1.9 — Environment Variables ✓ DONE (base) / ⏳ Add remaining fields

Current `.env` (already created):

```
DB_NAME=commitment_os
DB_USER=             # blank = Mac username (kanags)
DB_PASSWORD=         # blank = no password (Homebrew auth)
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

Fields to add to `.env` now:

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
GEMINI_CLASSIFY_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# ── WEEK 6 ───────────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-placeholder
SLACK_SIGNING_SECRET=placeholder

# ── WEEK 8 ───────────────────────────────────────────────
SENDGRID_API_KEY=placeholder
DEFAULT_FROM_EMAIL=noreply@commitment-os.com

# ── WEEK 9 ───────────────────────────────────────────────
ZOOM_CLIENT_ID=placeholder
ZOOM_CLIENT_SECRET=placeholder
ZOOM_WEBHOOK_SECRET_TOKEN=placeholder

# ── PHASE 2 ──────────────────────────────────────────────
AWS_ACCESS_KEY_ID=placeholder
AWS_SECRET_ACCESS_KEY=placeholder
AWS_S3_BUCKET_NAME=commitment-os-dev
AWS_S3_REGION=us-east-1
```

Create `.env.example` (same content, committed to git as reference):

```bash
cp backend/.env backend/.env.example
# Remove real values from .env.example — replace with placeholders
git add backend/.env.example
git commit -m "chore: add .env.example"
```

---

### Step 1.10 — Django Settings ⏳ NEXT

Replace `config/settings/base.py` entirely:

```python
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY    = config('DJANGO_SECRET_KEY')
DEBUG         = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost',
                       cast=lambda v: [s.strip() for s in v.split(',')])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    # Local
    'apps.accounts',
    'apps.meetings',
    'apps.commitments',
    'apps.notifications',
    'apps.analytics',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF     = 'config.urls'
AUTH_USER_MODEL  = 'accounts.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

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

CELERY_BROKER_URL        = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = 'django-db'
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = 'UTC'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM':                'HS256',
    'AUTH_HEADER_TYPES':        ('Bearer',),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'user': '1000/hour'},
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['authorization', 'content-type', 'accept', 'x-requested-with']

GEMINI_API_KEY          = config('GEMINI_API_KEY',          default='')
GEMINI_EXTRACTION_MODEL = config('GEMINI_EXTRACTION_MODEL', default='gemini-1.5-pro')
GEMINI_CLASSIFY_MODEL   = config('GEMINI_CLASSIFY_MODEL',   default='gemini-1.5-flash')
GEMINI_EMBEDDING_MODEL  = config('GEMINI_EMBEDDING_MODEL',  default='models/text-embedding-004')

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ   = True

SPECTACULAR_SETTINGS = {
    'TITLE': 'Commitment OS API',
    'DESCRIPTION': '''
## Commitment OS — Backend API

Extracts every commitment made in meetings, tracks it, detects conflicts, surfaces risk.

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
        {'name': 'dashboard',   'description': 'Aggregated stats for CoS'},
        {'name': 'meetings',    'description': 'Upload transcripts, receive webhooks'},
        {'name': 'commitments', 'description': 'CRUD, confirm, escalate, resolve'},
        {'name': 'conflicts',   'description': 'Cross-meeting contradiction detection'},
        {'name': 'analytics',   'description': 'Delivery rates, risk trends'},
        {'name': 'persons',     'description': 'Org participants + delivery stats'},
    ],
}
```

Create `config/settings/local.py`:

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL  = '/media/'

CELERY_TASK_ALWAYS_EAGER = False
```

Create `config/settings/production.py`:

```python
from .base import *
import sentry_sdk
from decouple import config

DEBUG = False
ALLOWED_HOSTS        = config('ALLOWED_HOSTS',        cast=lambda v: [s.strip() for s in v.split(',')])
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=lambda v: [s.strip() for s in v.split(',')])

DEFAULT_FILE_STORAGE    = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = config('AWS_S3_BUCKET_NAME')
AWS_S3_REGION_NAME      = config('AWS_S3_REGION', default='us-east-1')

sentry_sdk.init(dsn=config('SENTRY_DSN', default=''), traces_sample_rate=0.1)

SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'
```

---

### Step 1.11 — URLs, Swagger, Celery ⏳ NEXT

Replace `config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/', include([
        path('', include('apps.accounts.urls')),
        path('', include('apps.meetings.urls')),
        path('', include('apps.commitments.urls')),
        path('', include('apps.analytics.urls')),
    ])),

    path('api/schema/',       SpectacularAPIView.as_view(),                         name='schema'),
    path('api/schema/ui/',    SpectacularSwaggerView.as_view(url_name='schema'),    name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'),      name='redoc'),

    path('api/health/', lambda request: JsonResponse({'status': 'ok', 'version': '0.1.0'})),
]
```

Create `config/celery.py`:

```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('commitment_os')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

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

Update `config/__init__.py`:

```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

---

### Step 1.12 — First Migration + Superuser ⏳ NEXT (after steps 1.8–1.11)

```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# System check — must pass before migrating
python manage.py check

# Run migrations
python manage.py migrate

# Verify pgvector still enabled (already done, but confirm)
psql commitment_os -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# Create superuser (for Django admin + Swagger auth)
python manage.py createsuperuser
# Enter: username (e.g. admin), email, password

# Start server
python manage.py runserver

# Verify in browser:
# http://localhost:8000/api/health/       → {"status": "ok", "version": "0.1.0"}
# http://localhost:8000/admin/            → Django admin login
# http://localhost:8000/api/schema/ui/   → Swagger UI
```

---

### Step 1.13 — Gemini API Verification ⏳ TODO

Set `GEMINI_API_KEY` in `.env` first (https://aistudio.google.com/app/apikey), then:

```bash
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate

python << 'PYEOF'
from decouple import config
import google.generativeai as genai

key = config('GEMINI_API_KEY')
genai.configure(api_key=key)

print("1. Testing Gemini Flash...")
flash = genai.GenerativeModel("gemini-1.5-flash")
r = flash.generate_content('Return JSON only: {"status": "ok"}')
print(f"   Response: {r.text.strip()}")

print("2. Testing embeddings...")
result = genai.embed_content(
    model="models/text-embedding-004",
    content="Sarah will send the pricing deck by Friday",
    task_type="SEMANTIC_SIMILARITY"
)
dims = len(result['embedding'])
print(f"   Dimensions: {dims} (expected: 768)")
assert dims == 768

print("\nGemini working — start Week 1")
PYEOF
```

---

### Step 1.14 — GitHub Actions CI ⏳ TODO

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
        image: pgvector/pgvector:pg18
        env:
          POSTGRES_DB: commitment_os_test
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

      - name: Enable pgvector
        run: |
          PGPASSWORD=postgres psql -h localhost -U postgres \
            -d commitment_os_test \
            -c "CREATE EXTENSION IF NOT EXISTS vector;"

      - name: Run tests
        working-directory: backend
        env:
          DJANGO_SETTINGS_MODULE: config.settings.local
          DJANGO_SECRET_KEY: ci-secret-not-real
          DB_NAME: commitment_os_test
          DB_USER: postgres
          DB_PASSWORD: postgres
          DB_HOST: localhost
          REDIS_URL: redis://localhost:6379/0
          GEMINI_API_KEY: placeholder
        run: pytest --cov=apps --cov=extraction -v
EOF

git add .github/
git commit -m "ci: add backend CI workflow"
git push origin develop
```

---

### Step 1.15 — Setup Complete

```bash
cd ~/Documents/Programs/Verato
git add .
git commit -m "chore: scaffold complete — ready for Week 1"
git push origin develop
git tag v0.0.1-setup
git push origin v0.0.1-setup
```

---

## Part 2 — Daily Dev Workflow

```bash
# ── Start of session ─────────────────────────────────────
brew services list | grep -E "postgresql|redis"   # verify services
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# ── Four VS Code terminal tabs ───────────────────────────
# Tab 1 — Django API
python manage.py runserver
# → Swagger UI: http://localhost:8000/api/schema/ui/

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

## Part 3 — 12-Week Build Plan (Backend First)

> All work in Phases 1–2 is backend only.
> Swagger UI at `localhost:8000/api/schema/ui/` is your test interface.
> No frontend code is written until Phase 3.

---

### Week 1 — Extraction Engine
**Branch:** `feature/week1-extraction-engine`
**Goal:** Python function that takes transcript text and returns structured commitment JSON.

**Tasks:**
- [ ] `extraction/extractor.py` — `extract_commitments(meeting, transcript, participants)`
- [ ] `extraction/parser.py` — `safe_json_parse()` handles Gemini markdown fences
- [ ] `extraction/prompt_builder.py` — builds full prompt with calibration context slot
- [ ] Create 5 test transcripts in `extraction/tests/fixtures/`
- [ ] `extraction/tests/test_extractor.py` — test each fixture, assert on precision
- [ ] Iterate prompt until explicit commit precision > 85% across all 5
- [ ] `extraction/conflict_detector.py` — `get_embedding()` returning 768-float list

```bash
pytest extraction/tests/ -v
```

**Done when:** `pytest extraction/tests/` passes. Explicit commits extracted reliably.

---

### Week 2 — Django Models + API Skeleton
**Branch:** `feature/week2-models-api`
**Goal:** All tables in DB. Basic CRUD endpoints visible in Swagger UI.

**Tasks:**
- [ ] `apps/accounts/models.py` — Organisation, User, Person
- [ ] `apps/meetings/models.py` — Meeting, MeetingParticipant
- [ ] `apps/commitments/models.py` — all entities (see `03_data_model.md`)
- [ ] All migrations including pgvector index `RunSQL`
- [ ] Serializers for all models
- [ ] ViewSets — CRUD for commitments and meetings
- [ ] URL files for each app; wire into `config/urls.py`
- [ ] Open Swagger UI → verify all endpoints appear → test GET/POST

**Key Swagger test:**
```
POST /api/v1/auth/token/ → get JWT → Authorize
GET /api/v1/commitments/ → empty list, 200 OK
POST /api/v1/commitments/ → create test commitment
GET /api/v1/commitments/{id}/ → retrieve it
```

**Done when:** All migrations apply. CRUD works in Swagger with no errors.

---

### Week 3 — Ingestion Endpoint + Async Pipeline
**Branch:** `feature/week3-ingestion`
**Goal:** Upload transcript via Swagger → Celery processes → commitments appear in DB.

**Tasks:**
- [ ] `POST /api/v1/meetings/upload/` — accepts transcript text
- [ ] `apps/meetings/tasks.py` — `process_meeting` Celery task
- [ ] Wire extraction module into Celery task
- [ ] `GET /api/v1/meetings/{id}/status/` — polling endpoint
- [ ] Onboard first design partner — get 4 weeks of real transcripts
- [ ] Run their transcripts; review output with them

**Swagger test flow:**
```
POST /api/v1/meetings/upload/  → 202 + meeting_id
GET  /api/v1/meetings/{id}/status/ → poll until "complete"
GET  /api/v1/commitments/?meeting={id} → extracted commitments
```

**Done when:** Real transcript → Celery → commitments in DB. Design partner onboarded.

---

### Week 4 — Commitment Actions + Dashboard
**Branch:** `feature/week4-commitment-actions`
**Goal:** All CoS action endpoints built and tested in Swagger.

**Tasks:**
- [ ] `POST /api/v1/commitments/{id}/confirm/`
- [ ] `POST /api/v1/commitments/{id}/escalate/`
- [ ] `POST /api/v1/commitments/{id}/resolve/`
- [ ] `PATCH /api/v1/commitments/{id}/` — update owner, deadline
- [ ] `GET /api/v1/dashboard/` — aggregated stats
- [ ] Commitment list filters: `?status=at_risk`, `?owner={id}`, `?deadline_before=`
- [ ] `GET /api/v1/persons/`

**Done when:** Every endpoint the frontend will ever need is callable in Swagger.

---

### Week 5 — Risk Scoring + Status Automation
**Branch:** `feature/week5-risk-scoring`
**Goal:** Commitments change status automatically. Risk scores always fresh.

**Tasks:**
- [ ] `apps/commitments/risk.py` — `compute_risk_score()`
- [ ] `apps/commitments/tasks.py` — `recompute_risk_scores()` Celery task
- [ ] Celery Beat schedule — every 6 hours

**Done when:** Commitments approaching deadline auto-escalate to AT_RISK.

---

### Week 6 — Slack Nudges
**Branch:** `feature/week6-slack`
**Pre-req:** Create Slack app at https://api.slack.com/apps; set `SLACK_BOT_TOKEN` in `.env`

**Tasks:**
- [ ] `apps/notifications/slack.py` — Slack Bolt app
- [ ] `apps/notifications/tasks.py` — `send_deadline_nudges`
- [ ] Slack action handler — owner replies "done/delayed" → status update

**Done when:** Owner receives Slack DM. Replies "done". Dashboard shows DELIVERED.

---

### Week 7 — Analytics Endpoints
**Branch:** `feature/week7-analytics`

**Tasks:**
- [ ] `GET /api/v1/analytics/delivery-rates/`
- [ ] `GET /api/v1/analytics/risk-summary/`
- [ ] `GET /api/v1/analytics/commitment-volume/`

**Done when:** All analytics endpoints return correct aggregated data.

---

### Week 8 — Weekly Digest Email
**Branch:** `feature/week8-digest`
**Pre-req:** Set `SENDGRID_API_KEY` in `.env`

**Tasks:**
- [ ] Configure django-anymail with SendGrid
- [ ] HTML digest template (`templates/emails/weekly_digest.html`)
- [ ] `send_weekly_digest` Celery task — Monday 07:00 UTC

**Done when:** Digest email arrives, formats correctly, links work.

---

### Week 9 — Zoom Connector + Conflict Detection
**Branch:** `feature/week9-zoom-conflicts`
**Pre-req:** Zoom OAuth app created; ngrok installed

**Tasks:**
- [ ] `apps/meetings/connectors/zoom.py` — webhook handler
- [ ] Handle `meeting.transcript_completed` → queue `process_meeting`
- [ ] `extraction/conflict_detector.py` — `find_conflict_candidates()` + `classify_conflict()`
- [ ] `GET /api/v1/conflicts/` and `POST /api/v1/conflicts/{id}/resolve/`

**Done when:** End a Zoom meeting → auto-processed → conflicts detected.

---

### ✅ Backend Complete — Phase 2: Deploy to AWS

**AWS deployment checklist:**
```
□ Create RDS PostgreSQL 18 — enable pgvector after creation
□ Create ElastiCache Redis (cache.t4g.micro)
□ Create S3 bucket for transcripts
□ Create ECR repository for Docker images
□ Create ECS cluster
□ Write Dockerfile for Django (see mac_setup.md Phase 2 section)
□ Build + push Docker image to ECR
□ Create ECS task definitions: api / celery-worker / celery-beat
□ Create Application Load Balancer → HTTPS → ECS API
□ Store secrets in AWS Secrets Manager
□ Run Django migrations via ECS run-task
□ Verify: https://api.commitment-os.com/api/health/ → 200
□ Verify: https://api.commitment-os.com/api/schema/ui/ → Swagger UI
```

---

### Weeks 10–12 — Frontend on GCP (Google AI Studio → Cloud Run)

1. Open Google AI Studio (https://aistudio.google.com)
2. Generate Next.js frontend — describe each screen, paste endpoint details from Swagger
3. All API calls point to AWS ALB URL
4. Deploy to GCP Cloud Run

**Week 10** — scaffold + auth + dashboard
**Week 11** — commitment actions + analytics
**Week 12** — polish + deploy + convert design partners to paying contracts

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
pytest --cov=apps --cov-report=html

# Services (Homebrew)
brew services start postgresql@18
brew services start redis
brew services list

# Port conflicts
lsof -i :8000   # Django
lsof -i :5432   # Postgres
lsof -i :6379   # Redis
```

### Fill in .env as you reach each week
| Week | Credential | Where to get it |
|---|---|---|
| Now | `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| Week 6 | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | https://api.slack.com/apps |
| Week 8 | `SENDGRID_API_KEY` | https://app.sendgrid.com/settings/api_keys |
| Week 9 | `ZOOM_*` keys | https://marketplace.zoom.us/develop/create |
| Phase 2 | AWS credentials | https://console.aws.amazon.com |
| Phase 3 | GCP credentials | https://console.cloud.google.com |

---

*Backend-first: build and test everything in Swagger before touching the frontend.
Homebrew handles Postgres + Redis — no Docker needed locally.*
