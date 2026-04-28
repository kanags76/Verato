# Commitment OS — Build Plan
## Apple Silicon Mac · GitHub · Localhost First · AWS then GCP

> **Machine:** Apple Silicon Mac (M1/M2/M3)  
> **Source control:** GitHub (monorepo, private)  
> **Local dev:** Django + Celery run natively in venv · Postgres + Redis in Docker  
> **API testing:** Swagger UI at localhost:8000/api/schema/ui/ (no frontend needed)  
> **Deployment sequence:** Backend → AWS ECS first · Frontend → GCP Cloud Run second  
> **Frontend build tool:** Google AI Studio (generates Next.js, deployed to Cloud Run)

---

## The Three Phases — What You're Building and When

```
PHASE 1 — LOCAL BACKEND (Weeks 1–9)
────────────────────────────────────
Django REST API running on localhost:8000
All APIs tested via Swagger UI — no frontend written yet
Celery workers running locally for async tasks
Postgres + Redis in Docker (two commands, set and forget)

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

## On Docker — What You Actually Need

**Short answer:** Docker runs Postgres and Redis only. Two services. That's it.

Django, Celery, and all Python code runs natively in your virtual environment — not in Docker. This gives you faster reloads, easier debugging, and direct VS Code integration.

**Why Docker for just Postgres and Redis on Apple Silicon:**

Installing PostgreSQL 16 with the pgvector extension natively on M1/M2/M3 involves ARM architecture conflicts that waste hours. The Docker image `pgvector/pgvector:pg16` handles all of that in 30 seconds and just works.

```bash
# This is the full extent of your Docker usage in local dev
docker-compose up db redis -d   # start
docker-compose stop             # stop
docker-compose ps               # check status
```

**If you really want no Docker at all:** Install [Postgres.app](https://postgresapp.com) + pgvector manually + `brew install redis`. This works but adds setup friction on Apple Silicon. Docker is the faster path.

---

## On Swagger UI — Your Development Dashboard

Swagger UI is your testing interface for the entire backend development phase. You do not need a frontend to develop, test, or demonstrate the API.

```
http://localhost:8000/api/schema/ui/
```

What Swagger gives you:
- Every endpoint listed with full documentation
- Click any endpoint → fill in parameters → Execute → see real response
- JWT auth built in — log in once, all subsequent calls carry the token
- Auto-generated from your DRF code — always up to date, zero maintenance
- Share with design partners: "here's the live API, try it yourself"

**The workflow for every new endpoint:**
```
1. Write Django view + serializer
2. Open Swagger UI
3. Click the endpoint
4. Execute with test data
5. Verify response matches spec
6. Move on
```

---

## Part 1 — One-Time Setup

### Step 1.1 — Create the GitHub Repository

In your browser:

```
1. Go to https://github.com/new
2. Repository name:  commitment-os
3. Visibility:       Private
4. Initialise:       NO — do not add README, .gitignore, or licence
5. Click "Create repository"
6. Copy the SSH URL: git@github.com:YOUR_USERNAME/commitment-os.git
```

---

### Step 1.2 — SSH Key for GitHub

```bash
# Check if you already have one
ls ~/.ssh/id_ed25519.pub

# If not — generate one (press Enter for all prompts, or set a passphrase)
ssh-keygen -t ed25519 -C "your@email.com"

# Copy public key to clipboard (Mac)
cat ~/.ssh/id_ed25519.pub | pbcopy

# Add to GitHub:
# github.com → Settings → SSH and GPG keys → New SSH key → Paste → Save

# Test
ssh -T git@github.com
# Expected: "Hi YOUR_USERNAME! You've successfully authenticated..."
```

---

### Step 1.3 — Clone and Scaffold Monorepo

```bash
cd ~/projects   # or wherever you keep code

git clone git@github.com:YOUR_USERNAME/commitment-os.git
cd commitment-os

# Create structure
mkdir -p backend frontend .github/workflows

# Root .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
*.env
*.env.local
/backend/media/
/backend/staticfiles/

# Node
node_modules/
.next/

# OS
.DS_Store

# IDE
.vscode/settings.json
.idea/

# Never commit secrets
*.pem
*.key
EOF

cat > README.md << 'EOF'
# Commitment OS

Accountability layer for organisations.
Backend: Django REST (AWS ECS) | Frontend: Next.js (GCP Cloud Run)

## Local dev
1. `cd backend && docker-compose up db redis -d`
2. `source .venv/bin/activate && python manage.py runserver`
3. Open http://localhost:8000/api/schema/ui/
EOF

git add .
git commit -m "chore: initialise monorepo"
git push origin main

# Create develop branch — all feature work merges here
git checkout -b develop
git push origin develop
# In GitHub: Settings → Branches → set develop as default branch
```

---

### Step 1.4 — Branch Strategy

```
main         production. Protected. Merge from develop only.
develop      integration. All feature branches merge here.
feature/*    one per week, e.g. feature/week1-extraction-engine
fix/*        bug fixes, e.g. fix/risk-score-null-owner
```

```bash
# Start of each week
git checkout develop && git pull origin develop
git checkout -b feature/week1-extraction-engine

# Daily commits
git add . && git commit -m "feat(extraction): Gemini prompt builder"
git push origin feature/week1-extraction-engine

# End of week — PR on GitHub, merge to develop
git checkout develop && git pull origin develop
git branch -d feature/week1-extraction-engine
```

---

### Step 1.5 — Install Prerequisites (Apple Silicon Mac)

```bash
# ── Python 3.12 via pyenv ──────────────────────────────────────
brew install pyenv

# Add to ~/.zshrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

pyenv install 3.12.4
pyenv global 3.12.4
python --version    # → Python 3.12.4

# ── Node 20 via nvm ────────────────────────────────────────────
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install 20 && nvm use 20 && nvm alias default 20
node --version      # → v20.x.x

# ── Docker Desktop (for Postgres + Redis only) ─────────────────
# Download: https://www.docker.com/products/docker-desktop/
# Choose: Apple Silicon version
# After install:
docker --version
docker-compose --version

# ── Homebrew packages ──────────────────────────────────────────
brew install git    # if not already installed
```

---

### Step 1.6 — VS Code Setup

```bash
# Install VS Code: https://code.visualstudio.com (Apple Silicon build)
# Open project
code ~/projects/commitment-os

# Install extensions
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.black-formatter
code --install-extension batisteo.vscode-django
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension bradlc.vscode-tailwindcss
code --install-extension ms-azuretools.vscode-docker
code --install-extension humao.rest-client          # test APIs directly in VS Code
code --install-extension eamodio.gitlens
code --install-extension github.vscode-pull-request-github
```

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "emmet.includeLanguages": { "django-html": "html" },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/node_modules": true,
    "**/.next": true
  },
  "git.autofetch": true,
  "terminal.integrated.env.osx": {
    "DJANGO_SETTINGS_MODULE": "config.settings.local"
  }
}
```

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "batisteo.vscode-django",
    "humao.rest-client",
    "eamodio.gitlens",
    "github.vscode-pull-request-github"
  ]
}
```

```bash
git add .vscode/
git commit -m "chore: VS Code workspace config"
git push origin develop
```

---

### Step 1.7 — Docker Compose (Postgres + Redis Only)

```bash
cd ~/projects/commitment-os/backend

cat > docker-compose.yml << 'EOF'
version: '3.9'

# Runs Postgres (with pgvector) and Redis locally.
# Django and Celery run natively in your venv — NOT in Docker.
# Apple Silicon: pgvector/pgvector:pg16 is the correct ARM-compatible image.

services:
  db:
    image: pgvector/pgvector:pg16
    platform: linux/arm64           # Apple Silicon — explicit ARM image
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
    platform: linux/arm64           # Apple Silicon
    container_name: commitment_os_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

volumes:
  postgres_data:
    name: commitment_os_postgres_data
EOF

# Start services
docker-compose up db redis -d

# Verify
docker-compose ps
# Both should show: healthy

git add docker-compose.yml
git commit -m "chore(backend): docker-compose for Postgres + Redis (Apple Silicon)"
git push origin develop
```

---

### Step 1.8 — Django Project Scaffold

```bash
cd ~/projects/commitment-os/backend

# Virtual environment
python -m venv .venv
source .venv/bin/activate
which python   # → .../backend/.venv/bin/python

# Requirements
mkdir requirements

cat > requirements/base.txt << 'EOF'
django==5.1
djangorestframework==3.15
django-cors-headers==4.3
djangorestframework-simplejwt==5.3
django-filter==24.1
drf-spectacular==0.27
psycopg2-binary==2.9.9
pgvector==0.3.2
django-pgvector==0.3.0
celery==5.4
redis==5.0
django-celery-beat==2.6
django-celery-results==2.5
google-generativeai==0.8.0
slack-bolt==1.18
django-anymail[sendgrid]==11.0
django-storages[boto3]==1.14
boto3==1.34
requests==2.31
python-decouple==3.8
gunicorn==22.0
whitenoise==6.7
sentry-sdk==2.0
EOF

cat > requirements/local.txt << 'EOF'
-r base.txt
django-debug-toolbar==4.4
factory-boy==3.3
pytest-django==4.8
pytest-cov==5.0
model-bakery==1.19
ipython==8.26
black==24.0
flake8==7.0
EOF

cat > requirements/production.txt << 'EOF'
-r base.txt
EOF

pip install -r requirements/local.txt

# Django project
django-admin startproject config .

# Settings package
mkdir config/settings
mv config/settings.py config/settings/base.py
touch config/settings/__init__.py config/settings/local.py config/settings/production.py

# App directories
mkdir apps extraction

# Django apps
python manage.py startapp accounts   apps/accounts
python manage.py startapp meetings   apps/meetings
python manage.py startapp commitments apps/commitments
python manage.py startapp notifications apps/notifications
python manage.py startapp analytics  apps/analytics

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

git add .
git commit -m "feat(backend): Django scaffold with apps and extraction module"
git push origin develop
```

---

### Step 1.9 — Environment Variables

```bash
cd ~/projects/commitment-os/backend

cat > .env.example << 'EOF'
# ─────────────────────────────────────────────
# Commitment OS · Backend · Environment Variables
# cp .env.example .env  — then fill in real values
# .env is gitignored — NEVER commit it
# ─────────────────────────────────────────────

# Django
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=replace-with-50-random-chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Postgres — matches docker-compose.yml
DB_NAME=commitment_os
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis — matches docker-compose.yml
REDIS_URL=redis://localhost:6379/0

# ── WEEK 1 — fill this in now ─────────────────
# Get key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_EXTRACTION_MODEL=gemini-1.5-pro
GEMINI_CLASSIFY_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# ── WEEK 6 — fill in when building Slack nudges ──
# Create app at: https://api.slack.com/apps
SLACK_BOT_TOKEN=xoxb-placeholder
SLACK_SIGNING_SECRET=placeholder

# ── WEEK 8 — fill in when building email digest ──
# Get key at: https://app.sendgrid.com/settings/api_keys
SENDGRID_API_KEY=placeholder
DEFAULT_FROM_EMAIL=noreply@commitment-os.com

# ── WEEK 9 — fill in when building Zoom connector ──
# Create app at: https://marketplace.zoom.us/develop/create
ZOOM_CLIENT_ID=placeholder
ZOOM_CLIENT_SECRET=placeholder
ZOOM_WEBHOOK_SECRET_TOKEN=placeholder

# ── PHASE 2 — AWS (leave as placeholder for local dev) ──
AWS_ACCESS_KEY_ID=placeholder
AWS_SECRET_ACCESS_KEY=placeholder
AWS_S3_BUCKET_NAME=commitment-os-dev
AWS_S3_REGION=us-east-1
EOF

cp .env.example .env
# Now open .env and set GEMINI_API_KEY — it's the only one you need today
code .env

git add .env.example
git commit -m "chore: add .env.example with week-by-week fill-in guide"
git push origin develop
```

---

### Step 1.10 — Django Settings

**config/settings/base.py** — replace entire file:

```python
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY   = config('DJANGO_SECRET_KEY')
DEBUG        = config('DEBUG', default=False, cast=bool)
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
    'corsheaders.middleware.CorsMiddleware',   # Must be FIRST
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
        'USER':     config('DB_USER',     default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

# Celery
CELERY_BROKER_URL        = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = 'django-db'
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = 'UTC'

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM':                'HS256',
    'AUTH_HEADER_TYPES':        ('Bearer',),
}

# DRF
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

# CORS — overridden per environment
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['authorization', 'content-type', 'accept', 'x-requested-with']

# Gemini
GEMINI_API_KEY          = config('GEMINI_API_KEY',          default='')
GEMINI_EXTRACTION_MODEL = config('GEMINI_EXTRACTION_MODEL', default='gemini-1.5-pro')
GEMINI_CLASSIFY_MODEL   = config('GEMINI_CLASSIFY_MODEL',   default='gemini-1.5-flash')
GEMINI_EMBEDDING_MODEL  = config('GEMINI_EMBEDDING_MODEL',  default='models/text-embedding-004')

# Static
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ   = True
```

**config/settings/local.py**:

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Allow Swagger UI and future Next.js dev server
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',    # Swagger UI calling itself
    'http://localhost:3000',    # Next.js (Phase 3)
    'http://127.0.0.1:3000',
]

# Also allow all origins in local dev for Swagger UI convenience
CORS_ALLOW_ALL_ORIGINS = True   # Disable in production

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1']

EMAIL_BACKEND        = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL  = '/media/'

CELERY_TASK_ALWAYS_EAGER = False   # Set True to run tasks inline for debugging
```

**config/settings/production.py**:

```python
from .base import *
import sentry_sdk
from decouple import config

DEBUG = False
ALLOWED_HOSTS     = config('ALLOWED_HOSTS',       cast=lambda v: [s.strip() for s in v.split(',')])
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

### Step 1.11 — URLs, Swagger, Celery

**config/urls.py**:

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

    # ── API v1 ──────────────────────────────────────────────────
    path('api/v1/', include([
        path('', include('apps.accounts.urls')),
        path('', include('apps.meetings.urls')),
        path('', include('apps.commitments.urls')),
        path('', include('apps.analytics.urls')),
    ])),

    # ── Swagger / OpenAPI ────────────────────────────────────────
    # Raw OpenAPI schema (JSON) — used by Swagger UI + ReDoc + Postman
    path('api/schema/',
         SpectacularAPIView.as_view(),
         name='schema'),

    # Swagger UI — interactive API testing interface
    # This is your "dummy frontend" during backend development
    path('api/schema/ui/',
         SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),

    # ReDoc — clean API documentation view (share with design partners)
    path('api/schema/redoc/',
         SpectacularRedocView.as_view(url_name='schema'),
         name='redoc'),

    # ── Health check (used by AWS ALB) ───────────────────────────
    path('api/health/',
         lambda request: JsonResponse({'status': 'ok', 'version': '0.1.0'})),
]
```

**config/celery.py**:

```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('commitment_os')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_routes = {
    'apps.meetings.tasks.*':      {'queue': 'ai_pipeline'},
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.commitments.tasks.*':   {'queue': 'default'},
}

app.conf.beat_schedule = {
    'recompute-risk-scores':  {
        'task':     'apps.commitments.tasks.recompute_risk_scores',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'send-deadline-nudges':   {
        'task':     'apps.notifications.tasks.send_deadline_nudges',
        'schedule': crontab(minute=0, hour=9),
    },
    'send-weekly-digest':     {
        'task':     'apps.notifications.tasks.send_weekly_digest',
        'schedule': crontab(minute=0, hour=7, day_of_week='monday'),
    },
    'recompile-calibrations': {
        'task':     'apps.commitments.tasks.recompile_all_calibrations',
        'schedule': crontab(minute=0, hour=2, day_of_week='sunday'),
    },
}
```

**config/__init__.py**:

```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

---

### Step 1.12 — DRF Spectacular Config (Swagger Documentation)

Add to **config/settings/base.py**:

```python
# ── Swagger / drf-spectacular settings ─────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Commitment OS API',
    'DESCRIPTION': '''
## Commitment OS — Backend API

The accountability layer for organisations. Extracts every commitment made in
meetings, tracks it, detects cross-meeting conflicts, and surfaces risk.

### Authentication
All endpoints (except `/api/v1/auth/token/`) require a JWT Bearer token.

**To authenticate in Swagger UI:**
1. Call `POST /api/v1/auth/token/` with your username and password
2. Copy the `access` token from the response
3. Click the **Authorize** button (top right)
4. Enter: `Bearer <your-access-token>`
5. All subsequent requests will include the token automatically

### Base URL
- Local development: `http://localhost:8000`
- Production: `https://api.commitment-os.com`
    ''',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,   # Token survives page refresh
        'displayOperationId': False,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'docExpansion': 'list',         # Show endpoints collapsed by default
        'filter': True,                 # Enable search filter
        'showExtensions': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,          # Keep endpoints in definition order
    'TAGS': [
        {'name': 'auth',        'description': 'Authentication — get and refresh JWT tokens'},
        {'name': 'dashboard',   'description': 'CoS command centre aggregated stats'},
        {'name': 'meetings',    'description': 'Meeting ingestion — upload transcripts or receive webhooks'},
        {'name': 'commitments', 'description': 'Core entity — commitment CRUD, confirm, escalate, resolve'},
        {'name': 'conflicts',   'description': 'Cross-meeting contradiction detection and resolution'},
        {'name': 'analytics',   'description': 'Delivery rates, risk trends, accountability metrics'},
        {'name': 'persons',     'description': 'Org participants — owner assignment and delivery stats'},
    ],
}
```

---

### Step 1.13 — How to Use Swagger UI for API Testing

Once Django is running, open `http://localhost:8000/api/schema/ui/`

**Getting a JWT token in Swagger:**

```
1. Find POST /api/v1/auth/token/
2. Click "Try it out"
3. Enter:  {"username": "admin", "password": "yourpassword"}
4. Click Execute
5. Copy the "access" value from the response
6. Click the green "Authorize" button (top of page)
7. Type: Bearer <paste-access-token-here>
8. Click Authorize → Close
9. All subsequent calls are now authenticated
```

**Testing a new endpoint — the workflow:**

```
Write view in Django
     ↓
python manage.py runserver (if not already running)
     ↓
Refresh Swagger UI
     ↓
Find endpoint → Try it out → Fill parameters → Execute
     ↓
Verify: correct status code, correct response shape, correct data
     ↓
If wrong → fix view → repeat
     ↓
Write pytest test to lock in the expected behaviour
     ↓
Move to next endpoint
```

**VS Code REST Client alternative** (for quick one-off tests without opening browser):

Create `backend/api.http`:

```http
### Variables
@baseUrl = http://localhost:8000
@token = paste-your-token-here

### Get JWT token
POST {{baseUrl}}/api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "yourpassword"
}

### Health check
GET {{baseUrl}}/api/health/

### List commitments
GET {{baseUrl}}/api/v1/commitments/
Authorization: Bearer {{token}}

### Dashboard summary
GET {{baseUrl}}/api/v1/dashboard/
Authorization: Bearer {{token}}

### Upload a transcript
POST {{baseUrl}}/api/v1/meetings/upload/
Authorization: Bearer {{token}}
Content-Type: application/json

{
  "title": "Q2 Planning · Apr 22",
  "transcript_text": "Sarah: I'll have the pricing deck ready by Thursday. Tom: Great. I'll get the hiring brief to HR by end of week.",
  "occurred_at": "2026-04-22T14:00:00Z"
}
```

---

### Step 1.14 — First Migration + Verify

```bash
cd ~/projects/commitment-os/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local

# Verify Docker services are running
docker-compose ps   # Both should show healthy

# System check
python manage.py check

# Run migrations
python manage.py migrate

# Enable pgvector (run once)
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    cursor.execute(\"SELECT extname FROM pg_extension WHERE extname = 'vector';\")
    result = cursor.fetchone()
    print('pgvector:', 'ENABLED' if result else 'FAILED')
"

# Create superuser
python manage.py createsuperuser
# Enter: username (e.g. admin), email, password

# Start Django
python manage.py runserver

# Verify in browser:
# http://localhost:8000/api/health/        → {"status": "ok", "version": "0.1.0"}
# http://localhost:8000/admin/             → Django admin login
# http://localhost:8000/api/schema/ui/     → Swagger UI
# http://localhost:8000/api/schema/redoc/  → ReDoc documentation
```

---

### Step 1.15 — Gemini API Verification

```bash
cd ~/projects/commitment-os/backend
source .venv/bin/activate

python << 'PYEOF'
from decouple import config
import google.generativeai as genai

key = config('GEMINI_API_KEY')
if 'placeholder' in key or key == 'your-gemini-api-key-here':
    print("Set GEMINI_API_KEY in .env first")
    print("Get key: https://aistudio.google.com/app/apikey")
    exit(1)

genai.configure(api_key=key)

print("1. Testing Gemini Flash...")
flash = genai.GenerativeModel("gemini-1.5-flash")
r = flash.generate_content(
    'Return JSON only: {"status": "ok"}',
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.0
    )
)
print(f"   Response: {r.text.strip()}")

print("2. Testing embeddings (text-embedding-004)...")
result = genai.embed_content(
    model="models/text-embedding-004",
    content="Sarah will send the pricing deck by Friday",
    task_type="SEMANTIC_SIMILARITY"
)
dims = len(result['embedding'])
print(f"   Dimensions: {dims} (expected: 768)")
assert dims == 768

print("\n✓ Gemini working — start Week 1")
PYEOF
```

---

### Step 1.16 — GitHub Actions CI

```bash
cd ~/projects/commitment-os

cat > .github/workflows/backend-ci.yml << 'EOF'
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
        image: pgvector/pgvector:pg16
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
          python-version: '3.12'
          cache: 'pip'
          cache-dependency-path: backend/requirements/local.txt

      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements/local.txt

      - name: Enable pgvector
        run: |
          PGPASSWORD=postgres psql -h localhost -U postgres \
            -d commitment_os_test \
            -c "CREATE EXTENSION IF NOT EXISTS vector;"

      - name: Run tests
        working-directory: backend
        env:
          DJANGO_SETTINGS_MODULE: config.settings.local
          DJANGO_SECRET_KEY: ci-secret-not-used-in-production
          DB_NAME: commitment_os_test
          DB_USER: postgres
          DB_PASSWORD: postgres
          DB_HOST: localhost
          REDIS_URL: redis://localhost:6379/0
          GEMINI_API_KEY: placeholder-mocked-in-unit-tests
        run: |
          pytest --cov=apps --cov=extraction --cov-report=xml -v

      - uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml
          fail_ci_if_error: false
EOF

git add .github/
git commit -m "ci: add backend CI workflow"
git push origin develop
```

---

### Step 1.17 — Commit Setup Complete

```bash
cd ~/projects/commitment-os
git add .
git commit -m "chore: environment setup complete — ready for Week 1"
git push origin develop
git tag v0.0.1-setup
git push origin v0.0.1-setup
```

---

## Part 2 — Daily Dev Workflow

```bash
# ── Morning start ────────────────────────────────────────
cd ~/projects/commitment-os/backend
docker-compose up db redis -d     # if not already running

# ── Four VS Code terminal tabs ───────────────────────────
# Tab 1 — Django API
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver
# → Swagger UI: http://localhost:8000/api/schema/ui/

# Tab 2 — Celery worker (only needed when testing async tasks)
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
celery -A config worker --loglevel=info

# Tab 3 — Tests (run as needed)
source .venv/bin/activate
pytest -v --tb=short

# Tab 4 — Git / general commands
cd ~/projects/commitment-os

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
**Goal:** Python function that takes transcript text and returns structured commitment JSON. This is your most important code — take the full week.

**Tasks:**
- [ ] `extraction/extractor.py` — `extract_commitments(meeting, transcript, participants)`
- [ ] `extraction/parser.py` — `safe_json_parse()` handles Gemini markdown fences
- [ ] `extraction/prompt_builder.py` — builds full prompt with calibration context slot
- [ ] Create 5 test transcripts in `extraction/tests/fixtures/` (write them yourself — make them realistic)
- [ ] `extraction/tests/test_extractor.py` — test each fixture, assert on precision
- [ ] Iterate prompt until explicit commit precision > 85% across all 5
- [ ] `extraction/conflict_detector.py` — `get_embedding()` returning 768-float list

```bash
pytest extraction/tests/ -v
```

**Swagger involvement this week:** None — pure Python work. No Django views yet.

**Done when:** `pytest extraction/tests/` passes. You can extract explicit commits reliably.

---

### Week 2 — Django Models + API Skeleton
**Branch:** `feature/week2-models-api`  
**Goal:** All tables in DB. Basic CRUD endpoints visible and callable in Swagger UI.

**Tasks:**
- [ ] `apps/accounts/models.py` — Organisation, User, Person
- [ ] `apps/meetings/models.py` — Meeting, MeetingParticipant
- [ ] `apps/commitments/models.py` — all entities (see `02_data_model.md`)
- [ ] All migrations including pgvector index `RunSQL`
- [ ] Serializers for all models
- [ ] ViewSets — CRUD for commitments and meetings
- [ ] URL files for each app; wire into `config/urls.py`
- [ ] Open Swagger UI → verify all endpoints appear → test GET/POST

**Key Swagger test:**
```
Swagger UI → POST /api/v1/auth/token/ → get JWT
Authorize with token
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
- [ ] `POST /api/v1/meetings/upload/` — accepts transcript text or file
- [ ] `apps/meetings/tasks.py` — `process_meeting` Celery task (full pipeline)
- [ ] Wire extraction module into Celery task
- [ ] `GET /api/v1/meetings/{id}/status/` — polling endpoint
- [ ] Test via Swagger: upload transcript → poll status → GET commitments

**Swagger test flow:**
```
Swagger → POST /api/v1/meetings/upload/
  body: {"title": "Test meeting", "transcript_text": "...", "occurred_at": "..."}
  → 202 Accepted + meeting_id + poll_url

Watch Celery terminal — should process and log extraction
Poll GET /api/v1/meetings/{id}/status/ until "complete"
GET /api/v1/commitments/?meeting={id} → commitments extracted
```

- [ ] **Onboard first design partner** — get 4 weeks of their real transcripts
- [ ] Run their transcripts; review output with them at end of week

**Done when:** Real transcript → Celery → commitments in DB. Design partner onboarded.

---

### Week 4 — Commitment Review + Action Endpoints
**Branch:** `feature/week4-commitment-actions`  
**Goal:** All CoS action endpoints built and tested in Swagger. These power the frontend later.

**Tasks:**
- [ ] `POST /api/v1/commitments/{id}/confirm/` — PENDING_REVIEW → ACTIVE
- [ ] `POST /api/v1/commitments/{id}/escalate/` — create EscalationEvent + dispatch
- [ ] `POST /api/v1/commitments/{id}/resolve/` — mark delivered/deferred/cancelled
- [ ] `PATCH /api/v1/commitments/{id}/` — update owner, deadline
- [ ] `GET /api/v1/dashboard/` — aggregated stats (overdue, at-risk, on-track, rate)
- [ ] Commitment list filters: `?status=at_risk`, `?owner={id}`, `?deadline_before=`
- [ ] `GET /api/v1/persons/` — participant list for owner picker

**Swagger test all new endpoints with real commitment data from Week 3.**

**Done when:** Every endpoint the frontend will ever need is callable in Swagger and returns correct data.

---

### Week 5 — Risk Scoring + Status Automation
**Branch:** `feature/week5-risk-scoring`  
**Goal:** Commitments change status automatically. Risk scores always fresh.

**Tasks:**
- [ ] `apps/commitments/risk.py` — `compute_risk_score()` deterministic formula
- [ ] `apps/commitments/tasks.py` — `recompute_risk_scores()` Celery task
- [ ] Celery Beat schedule — every 6 hours
- [ ] Verify risk score updates via Swagger: GET commitment → check risk_score changes after deadline passes

**Swagger test:**
```
GET /api/v1/commitments/{id}/   → note current risk_score
# Manually update commitment deadline to yesterday via PATCH
GET /api/v1/commitments/{id}/   → risk_score should now be ~1.0, status AT_RISK
```

**Done when:** Commitments approaching deadline auto-escalate to AT_RISK status.

---

### Week 6 — Slack Nudges
**Branch:** `feature/week6-slack`  
**Pre-req:** Create Slack app at https://api.slack.com/apps; set `SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET` in `.env`

**Tasks:**
- [ ] `apps/notifications/slack.py` — Slack Bolt app instance
- [ ] `apps/notifications/tasks.py` — `send_deadline_nudges`, `send_slack_nudge`
- [ ] Slack action handler — owner replies "done/delayed" → status update via API
- [ ] Test: create commitment with deadline in 48hrs → manually trigger task → verify Slack DM

**Test manually (bypass Celery Beat for testing):**
```bash
python manage.py shell -c "
from apps.notifications.tasks import send_deadline_nudges
send_deadline_nudges()
"
```

**Done when:** Owner receives Slack DM. Replies "done". Dashboard shows DELIVERED.

---

### Week 7 — Analytics Endpoints
**Branch:** `feature/week7-analytics`  
**Goal:** All analytics endpoints ready for frontend to consume.

**Tasks:**
- [ ] `GET /api/v1/analytics/delivery-rates/` — by person, team, date range
- [ ] `GET /api/v1/analytics/risk-summary/` — distribution snapshot
- [ ] `GET /api/v1/analytics/commitment-volume/` — commits over time

**Swagger test:**
```
GET /api/v1/analytics/delivery-rates/?days=30
GET /api/v1/analytics/risk-summary/
```

**Done when:** All analytics endpoints return correct aggregated data.

---

### Week 8 — Weekly Digest Email
**Branch:** `feature/week8-digest`  
**Pre-req:** Set `SENDGRID_API_KEY` in `.env`

**Tasks:**
- [ ] Configure django-anymail with SendGrid
- [ ] HTML digest email template (`templates/emails/weekly_digest.html`)
- [ ] `send_weekly_digest` Celery task
- [ ] Celery Beat — Monday 07:00 UTC
- [ ] Manual trigger test: send digest to yourself

```bash
python manage.py shell -c "
from apps.notifications.tasks import send_weekly_digest
send_weekly_digest()
"
```

**Done when:** Digest email arrives, formats correctly, links work.

---

### Week 9 — Zoom Connector + Conflict Detection
**Branch:** `feature/week9-zoom-conflicts`  
**Pre-req:** Zoom OAuth app created; ngrok installed

**Zoom tasks:**
- [ ] `apps/meetings/connectors/zoom.py` — webhook handler with signature verification
- [ ] Handle `meeting.transcript_completed` event → queue `process_meeting`
- [ ] Use ngrok to expose localhost for Zoom testing: `ngrok http 8000`

**Conflict detection tasks:**
- [ ] `extraction/conflict_detector.py` — `find_conflict_candidates()` + `classify_conflict()`
- [ ] Wire into `process_meeting` Celery task
- [ ] `GET /api/v1/conflicts/` and `POST /api/v1/conflicts/{id}/resolve/`

**Swagger test:**
```
GET /api/v1/conflicts/           → list unresolved conflicts
POST /api/v1/conflicts/{id}/resolve/   → mark resolved
```

**Done when:** End a Zoom meeting → auto-processed → conflicts detected if any exist.

---

### ✅ Backend Complete — Phase 2: Deploy to AWS

After Week 9, the backend is feature-complete for Phase 1. Before building the frontend, deploy to AWS.

**AWS deployment checklist (do once, takes ~half a day):**
```
□ Create AWS account (or use existing)
□ Create RDS PostgreSQL 16 — enable pgvector extension after creation
□ Create ElastiCache Redis (cache.t4g.micro)
□ Create S3 bucket for transcripts
□ Create ECR repository for Docker images
□ Create ECS cluster
□ Write Dockerfile for Django
□ Build + push Docker image to ECR
□ Create three ECS task definitions: api / celery-worker / celery-beat
□ Create ECS services for each
□ Create Application Load Balancer → HTTPS → ECS API
□ Store all secrets in AWS Secrets Manager
□ Run Django migrations via ECS run-task
□ Verify: https://api.commitment-os.com/api/health/ → 200
□ Verify: https://api.commitment-os.com/api/schema/ui/ → Swagger UI live
```

Once the Swagger UI loads from the AWS URL, the backend is production-ready. The frontend can now be built against the live API.

---

### Weeks 10–12 — Frontend on GCP (Google AI Studio → Cloud Run)

**How this works:**

1. Open [Google AI Studio](https://aistudio.google.com)
2. Use it to generate the Next.js frontend components — describe each screen, reference the API spec from Swagger, paste endpoint details as context
3. All API calls point to your AWS ALB URL (`https://api.commitment-os.com`)
4. Deploy the generated Next.js app to GCP Cloud Run

**Week 10 — Frontend scaffold + auth + dashboard**
- [ ] Generate Next.js project structure in AI Studio
- [ ] Implement API client (`lib/api/client.ts`) — JWT Bearer, typed fetch
- [ ] Login page → calls `POST /api/v1/auth/token/`
- [ ] Dashboard page → calls `GET /api/v1/dashboard/`
- [ ] Commitment list → calls `GET /api/v1/commitments/`

**Week 11 — Commitment actions + analytics**
- [ ] Commitment detail page + escalation modal
- [ ] Extraction review screen
- [ ] Conflicts review page
- [ ] Analytics dashboard

**Week 12 — Polish + deploy + convert design partners**
- [ ] Deploy Next.js to GCP Cloud Run
- [ ] Set `NEXT_PUBLIC_API_URL` = your AWS ALB domain
- [ ] End-to-end test: meeting → extraction → dashboard → escalation
- [ ] Present ROI summary to design partner exec
- [ ] Send annual contract proposal

---

## Part 4 — Helper Scripts

```bash
mkdir -p ~/projects/commitment-os/backend/scripts

# ── start_dev.sh — run this each morning ──────────────────
cat > ~/projects/commitment-os/backend/scripts/start_dev.sh << 'EOF'
#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Starting Commitment OS local services..."
docker-compose up db redis -d

source .venv/bin/activate

# Wait for Postgres
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
  echo "  Waiting for Postgres..."
  sleep 2
done

python manage.py migrate --settings=config.settings.local

echo ""
echo "✓ Ready. Open these tabs in VS Code terminal:"
echo ""
echo "  Tab 1 (API):    python manage.py runserver"
echo "  Tab 2 (Celery): celery -A config worker --loglevel=info"
echo ""
echo "  Swagger UI:  http://localhost:8000/api/schema/ui/"
echo "  ReDoc docs:  http://localhost:8000/api/schema/redoc/"
echo "  Admin:       http://localhost:8000/admin/"
EOF
chmod +x ~/projects/commitment-os/backend/scripts/start_dev.sh

# ── test_gemini.sh ─────────────────────────────────────────
cat > ~/projects/commitment-os/backend/scripts/test_gemini.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -c "
from decouple import config
import google.generativeai as genai
genai.configure(api_key=config('GEMINI_API_KEY'))
r = genai.GenerativeModel('gemini-1.5-flash').generate_content(
    'Return JSON: {\"ok\": true}',
    generation_config=genai.GenerationConfig(response_mime_type='application/json')
)
print(f'Flash: {r.text.strip()}')
emb = genai.embed_content(model='models/text-embedding-004', content='test', task_type='SEMANTIC_SIMILARITY')
print(f'Embeddings: {len(emb[\"embedding\"])} dims')
print('Gemini OK')
"
EOF
chmod +x ~/projects/commitment-os/backend/scripts/test_gemini.sh

# ── reset_db.sh — nuclear option ──────────────────────────
cat > ~/projects/commitment-os/backend/scripts/reset_db.sh << 'EOF'
#!/bin/bash
echo "WARNING: Wipes all local data. Ctrl+C to cancel."
sleep 3
cd "$(dirname "$0")/.."
docker-compose down -v
docker-compose up db redis -d
source .venv/bin/activate
sleep 5
python manage.py migrate --settings=config.settings.local
python manage.py shell --settings=config.settings.local -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;')
print('pgvector enabled')
"
python manage.py createsuperuser --settings=config.settings.local
EOF
chmod +x ~/projects/commitment-os/backend/scripts/reset_db.sh

cd ~/projects/commitment-os
git add backend/scripts/
git commit -m "chore: add dev helper scripts"
git push origin develop
```

---

## Part 5 — Reference

### URLs during local development
| URL | What it is |
|---|---|
| `http://localhost:8000/api/schema/ui/` | **Swagger UI — your main test interface** |
| `http://localhost:8000/api/schema/redoc/` | ReDoc — clean API docs to share |
| `http://localhost:8000/api/schema/` | Raw OpenAPI JSON schema |
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
pytest apps/commitments/ -v          # test one app
pytest -k "test_risk" -v             # test by name pattern
pytest --cov=apps --cov-report=html  # with coverage

# Celery — run task synchronously for debugging (no worker needed)
# In .env: CELERY_TASK_ALWAYS_EAGER=True  → tasks run inline

# Docker
docker-compose up db redis -d        # start
docker-compose stop                  # stop
docker-compose ps                    # status
docker-compose down -v               # nuclear: delete all data

# Port conflicts
lsof -i :8000   # Django
lsof -i :5432   # Postgres
lsof -i :6379   # Redis
```

### Fill in .env as you reach each week
| Week | Credential needed | Where to get it |
|---|---|---|
| Now | `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| Week 6 | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | https://api.slack.com/apps |
| Week 8 | `SENDGRID_API_KEY` | https://app.sendgrid.com/settings/api_keys |
| Week 9 | `ZOOM_*` keys | https://marketplace.zoom.us/develop/create |
| Week 9 | ngrok | https://ngrok.com (Zoom webhook testing) |
| Phase 2 | AWS credentials | https://console.aws.amazon.com |
| Phase 3 | GCP credentials | https://console.cloud.google.com |

---

*Feed this to Claude Code in VS Code. Start at Step 1.1.  
Backend-first: build and test everything in Swagger before touching the frontend.  
Docker is two services only — set and forget.*
