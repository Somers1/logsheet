import os
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

UNCHAINED = os.environ.get('UNCHAINED_TOML_PREFIX')

MAIN_APP = Path(__file__).resolve().parent
BASE_DIR = MAIN_APP.parent
PROJECT_NAME = 'logsheet'
config_name = Path('system.toml')
if toml_prefix := UNCHAINED:
    config_name = Path(f'system.{toml_prefix}.toml')
config_path = Path(f'/etc/{PROJECT_NAME}') / config_name
config_path = config_path if config_path.exists() else BASE_DIR / config_name
SYSTEM_CONFIG = tomllib.load(config_path.open('rb'))

GLOBAL_CONFIG = SYSTEM_CONFIG['global']
DATABASE_CONFIG = SYSTEM_CONFIG['database']
DJANGO_CONFIG = SYSTEM_CONFIG['django']
CELERY_CONFIG = SYSTEM_CONFIG['celery']
CACHE_CONFIG = SYSTEM_CONFIG['cache']
TASK_QUEUES_CONFIG = SYSTEM_CONFIG['task_queues'][GLOBAL_CONFIG['queue_mode']]
LANGFUSE_CONFIG = SYSTEM_CONFIG['langfuse']
TIMESHEET = SYSTEM_CONFIG['timesheet']

ENVIRONMENT = SYSTEM_CONFIG['environment']
os.environ.update(ENVIRONMENT)

SECRET_KEY = DJANGO_CONFIG.get('secret_key')
SITE_ID = 1

DEBUG = DJANGO_CONFIG.get('debug')

ALLOWED_HOSTS = DJANGO_CONFIG.get('allowed_hosts')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'knox',
    'project'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '%s.urls' % PROJECT_NAME
TEMPLATE_ROOT = BASE_DIR / 'templates'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_ROOT],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = f'{MAIN_APP.name}.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DATABASE_CONFIG.get('name', PROJECT_NAME),
        'USER': DATABASE_CONFIG.get('user', PROJECT_NAME),
        'PASSWORD': DATABASE_CONFIG.get('pass', PROJECT_NAME),
        'PORT': DATABASE_CONFIG.get('port', 5432),
        'HOST': DATABASE_CONFIG.get('host', 'localhost'),
    },
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
AS_DB_TIME_ZONE = ZoneInfo(TIME_ZONE)
LOCAL_TIME_ZONE = GLOBAL_CONFIG['timezone']
AS_LOCAL_TIME_ZONE = ZoneInfo(LOCAL_TIME_ZONE)
USE_I18N = True
USE_TZ = True


CELERY_BROKER_URL = 'redis://%(target)s:%(port)s/%(name)s' % CELERY_CONFIG
CELERY_ACCEPTED_CONTENT = ['application/json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_IGNORE_RESULT = CELERY_CONFIG.get('ignore_results', True)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_SEND_EVENTS = True
CELERY_TASK_ROUTES = {task_route: {'queue': TASK_QUEUES_CONFIG[task_route]} for task_route in TASK_QUEUES_CONFIG}

cache_host = CACHE_CONFIG.get('host', 'localhost')
cache_port = CACHE_CONFIG.get('port', '6379')
cache_db = CACHE_CONFIG.get('db', '10')
cache_socket = f'redis://{cache_host}:{cache_port}/{cache_db}'


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': cache_socket,
        'TIMEOUT': int(CACHE_CONFIG.get('timeout', '10800')),
        'OPTIONS': {
            'db': CACHE_CONFIG.get('db', '10')
        }
    },
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
for folder in [STATIC_ROOT, MEDIA_ROOT, TEMPLATE_ROOT]:
    folder.mkdir(exist_ok=True, parents=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = DJANGO_CONFIG['cors_allowed_origin']
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = DJANGO_CONFIG['csrf_trusted_origins']

REST_KNOX = {
    'USER_SERIALIZER': 'knox.serializers.UserSerializer',
    'AUTO_REFRESH': True,
}

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter'
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'knox.auth.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FileUploadParser',
    ],
}


if UNCHAINED:
    GDAL_LIBRARY_PATH = '/opt/lib/libgdal.so'
    GEOS_LIBRARY_PATH = '/opt/lib/libgeos_c.so'

if not UNCHAINED:
    REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'
    for folder in [STATIC_ROOT, MEDIA_ROOT, TEMPLATE_ROOT]:
        folder.mkdir(exist_ok=True, parents=True)
