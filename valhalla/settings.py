"""
Django settings for valhalla project.

Generated by 'django-admin startproject' using Django 1.10.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
from lcogt_logging import LCOGTFormatter

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/
SECRET_KEY = os.getenv('SECRET_KEY', '*j6j4auodqdo=nab#3je9mn6hkzxyxc%5#=ndj6np4o#g--=rw')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['valhallascheduler.lco.gtn', 'valhalla.lco.gtn', 'observe.lco.global', 'observe-beta.lco.global']

SITE_ID = 1

ADMINS = [
    ('Austin Riba', 'ariba@lco.global'), ('Jon Nation', 'jnation@lco.global'), ('Eric Saunders', 'esaunders@lco.global')
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'registration',  # must come before admin to use custom templates
    'django.contrib.admin',
    'rest_framework',
    'django_filters',
    'rest_framework.authtoken',
    'bootstrap3',
    'oauth2_provider',
    'corsheaders',
    'django_extensions',
    'valhalla.accounts',
    'valhalla.userrequests',
    'valhalla.proposals',
    'valhalla.sciapplications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'valhalla.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'valhalla.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', '')
    }
}

CACHES = {
    'default': {
        'BACKEND': os.getenv('CACHE_BACKEND', 'django.core.cache.backends.dummy.DummyCache'),
        'LOCATION': os.getenv('CACHE_LOCATION', 'unique-snowflake')
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': LCOGTFormatter
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'rise_set': {
            'level': 'WARNING'
        }
    }
}
# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'valhalla.accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
    'oauth2_provider.backends.OAuth2Backend',
]

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 86400 * 360,  # 1 year
    'REFRESH_TOKEN_EXPIRE_SECONDS': 86400 * 360  # 1 year
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = r'^/api/.*$|^/o/.*'


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

DATETIME_FORMAT = 'Y-m-d H:i:s'

USE_I18N = True

USE_L10N = False

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, '_static')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

ACCOUNT_ACTIVATION_DAYS = 7
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = os.getenv('EMAIL_PORT', 587)
DEFAULT_FROM_EMAIL = 'Webmaster <portal@lco.global>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost')
POND_URL = os.getenv('POND_URL', 'http://localhost')
CONFIGDB_URL = os.getenv('CONFIGDB_URL', 'http://localhost')

REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': (
        'valhalla.accounts.throttling.AllowStaffUserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '50000/day',
        'userrequests.cancel': '1000/day',
        'userrequests.validate': '100000/day'
    }
}

CELERY_TASK_ALWAYS_EAGER = not os.getenv('CELERY_ENABLED', False)
CELERY_BROKER_URL = os.getenv('BROKER_URL', 'memory://localhost')
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_BEAT_SCHEDULE = {
    'time-accounting-every-hour': {
        'task': 'valhalla.proposals.tasks.run_accounting',
        'schedule': 3600.0
    },
    'expire-requests-every-5-minutes': {
        'task': 'valhalla.userrequests.tasks.expire_requests',
        'schedule': 300.0
    }
}
try:
    from local_settings import *  # noqa
except ImportError:
    pass

try:
    INSTALLED_APPS += LOCAL_INSTALLED_APPS  # noqa
    ALLOWED_HOSTS += LOCAL_ALLOWED_HOSTS  # noqa
except NameError:
    pass
