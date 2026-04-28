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
