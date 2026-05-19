from .base import *
from decouple import config

DEBUG = False
ALLOWED_HOSTS       = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])
CORS_ALLOW_ALL_ORIGINS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
    },
}

# S3 file storage — only enabled if bucket name is provided
_s3_bucket = config('AWS_S3_BUCKET_NAME', default='')
if _s3_bucket:
    DEFAULT_FILE_STORAGE    = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_STORAGE_BUCKET_NAME = _s3_bucket
    AWS_S3_REGION_NAME      = config('AWS_S3_REGION', default='us-east-1')

MEDIA_ROOT = BASE_DIR / 'mediafiles'
MEDIA_URL  = '/media/'

SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'
SECURE_PROXY_SSL_HEADER     = ('HTTP_X_FORWARDED_PROTO', 'https')
