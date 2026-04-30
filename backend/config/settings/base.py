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

ROOT_URLCONF       = 'config.urls'
AUTH_USER_MODEL    = 'accounts.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
WSGI_APPLICATION   = 'config.wsgi.application'

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

# Vertex AI — auth via ADC (gcloud auth application-default login), no API key
GOOGLE_CLOUD_PROJECT    = config('GOOGLE_CLOUD_PROJECT',    default='verato')
GOOGLE_CLOUD_LOCATION   = config('GOOGLE_CLOUD_LOCATION',   default='us-central1')
GEMINI_EXTRACTION_MODEL = config('GEMINI_EXTRACTION_MODEL', default='gemini-2.5-flash-lite')
GEMINI_CLASSIFY_MODEL   = config('GEMINI_CLASSIFY_MODEL',   default='gemini-2.5-flash-lite')
GEMINI_EMBEDDING_MODEL  = config('GEMINI_EMBEDDING_MODEL',  default='text-embedding-004')

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

SPECTACULAR_SETTINGS = {
    'TITLE': 'Verato API',
    'DESCRIPTION': '''
## Verato — Backend API

Extracts every commitment made in meetings, assigns ownership, scores risk, and nudges before it slips.

### Authentication
All endpoints (except /api/v1/auth/token/) require a JWT Bearer token.
1. POST /api/v1/auth/token/ with username + password
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
        {'name': 'dashboard',   'description': 'Summary stats for CoS command centre'},
        {'name': 'meetings',    'description': 'Upload transcripts, import prior commitments, receive webhooks'},
        {'name': 'commitments', 'description': 'Confirm, escalate, resolve, defer, list with filters'},
        {'name': 'persons',     'description': 'Org participants, used for owner picker'},
    ],
}
