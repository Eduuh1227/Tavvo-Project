"""Environment-driven configuration; PostgreSQL is required in every environment."""
import os
from pathlib import Path
from urllib.parse import unquote, urlparse
from core.environment import load_local_environment

load_local_environment()

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.getenv('TAVVO_ENV', 'development')
DEBUG = ENVIRONMENT == 'development'
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
if os.getenv('VERCEL') == '1':
    # Platform-generated hostnames, never unvalidated request headers.
    for variable in ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
        host = os.getenv(variable)
        if host:
            ALLOWED_HOSTS.append(host)
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'rest_framework', 'drf_spectacular', 'core', 'identity', 'restaurants',
    'catalog', 'publishing', 'tables', 'audit',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'identity.middleware.SessionPolicyMiddleware',
    'core.middleware.RequestIdMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = 'identity.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'pt-br'
database = urlparse(os.environ['DATABASE_URL'])
if database.scheme not in ('postgres', 'postgresql'):
    raise ValueError('DATABASE_URL must use PostgreSQL')
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': unquote(database.path.lstrip('/')), 'USER': unquote(database.username or ''),
    'PASSWORD': unquote(database.password or ''), 'HOST': database.hostname, 'PORT': database.port or 5432,
    'ATOMIC_REQUESTS': True, 'CONN_MAX_AGE': 0,
    'OPTIONS': {'sslmode': os.getenv('DATABASE_SSLMODE', 'prefer'), 'prepare_threshold': None},
    'DISABLE_SERVER_SIDE_CURSORS': True,
}}
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
]
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800
TAVVO_SESSION_ABSOLUTE_SECONDS = SESSION_COOKIE_AGE
TAVVO_SESSION_IDLE_SECONDS = 1800
SESSION_COOKIE_NAME = 'tavvo_session'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = 'identity.views.csrf_failure'
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
if os.getenv('VERCEL') == '1':
    CSRF_TRUSTED_ORIGINS += ['https://' + host for host in ALLOWED_HOSTS if host.endswith('.vercel.app')]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = os.getenv('DJANGO_HTTPS_REDIRECT', 'false').lower() == 'true'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_REFERRER_POLICY = 'same-origin'
TAVVO_MFA_ENCRYPTION_KEY = os.environ['TAVVO_MFA_ENCRYPTION_KEY']
deployment_host = os.getenv('VERCEL_URL') or os.getenv('VERCEL_BRANCH_URL')
deployment_origin = f'https://{deployment_host}' if deployment_host else None
TAVVO_ADMIN_ORIGIN = os.getenv('TAVVO_ADMIN_ORIGIN', deployment_origin or 'http://localhost:5173')
TAVVO_PUBLIC_ORIGIN = os.getenv('TAVVO_PUBLIC_ORIGIN', deployment_origin or 'http://localhost:3000')
PUBLIC_SITE_URL = TAVVO_PUBLIC_ORIGIN
TAVVO_PASSWORD_RESET_URL = TAVVO_ADMIN_ORIGIN + '/reset-password'
PASSWORD_RESET_TIMEOUT = 1800
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '1025'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Tavvo <no-reply@localhost>')
IMAGE_STORAGE_BACKEND = os.getenv('IMAGE_STORAGE_BACKEND', 's3')
if IMAGE_STORAGE_BACKEND not in ('s3', 'vercel_blob'):
    raise ValueError('Unsupported image storage backend')
S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL') or None
S3_BUCKET = os.getenv('S3_BUCKET', 'tavvo-images')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
S3_SESSION_TOKEN = os.getenv('S3_SESSION_TOKEN') or None
IMAGE_MAX_BYTES = int(os.getenv('IMAGE_MAX_BYTES', str(5 * 1024 * 1024)))
REST_FRAMEWORK = {
    'URL_FORMAT_OVERRIDE': None,
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'core.exceptions.api_exception_handler',
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'COERCE_DECIMAL_TO_STRING': True,
}
SPECTACULAR_SETTINGS = {
    'TITLE': 'Tavvo Restaurants API', 'VERSION': '1.0.0',
    'DESCRIPTION': 'Shared tenant-isolated restaurant platform. Decimal amounts are strings.',
    'COMPONENT_SPLIT_REQUEST': True,
    'ENUM_NAME_OVERRIDES': {
        'ActiveStatusEnum': [('active', 'Active'), ('inactive', 'Inactive')],
        'DomainStatusEnum': [('pending', 'Pending verification'), ('verified', 'Verified'), ('disabled', 'Disabled')],
        'MembershipStatusEnum': [('active', 'Active'), ('revoked', 'Revoked')],
    },
}
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
if ENVIRONMENT in ('production', 'demo'):
    if len(SECRET_KEY) < 50 or '*' in ALLOWED_HOSTS:
        raise ValueError('Production requires a strong secret and explicit hosts')
    if IMAGE_STORAGE_BACKEND == 's3' and (not S3_ACCESS_KEY or not S3_SECRET_KEY):
        raise ValueError('Production S3 credentials must be configured')
    if IMAGE_STORAGE_BACKEND == 'vercel_blob' and not os.getenv('BLOB_READ_WRITE_TOKEN'):
        raise ValueError('Private Blob credentials must be configured')
