"""
Django settings for AirNation project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import environ
from pathlib import Path
import os
import django_heroku
import dj_database_url
from decouple import config
import json
from django.contrib.messages import constants as messages




# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

GOOGLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Initialize environment variables
env = environ.Env(
    EMAIL_USE_TLS=(bool, True),
    EMAIL_PORT=(int, 587),
    SESSION_TIMEOUT=(int, 30 * 60),  # Default: 30 minutes
    SECURE_HSTS_SECONDS=(int, 31536000),  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    SECURE_HSTS_PRELOAD=(bool, True),
    SECURE_CONTENT_TYPE_NOSNIFF=(bool, True),
    SECURE_BROWSER_XSS_FILTER=(bool, True),
    X_FRAME_OPTIONS=(str, "DENY"),
    MAX_IMAGE_SIZE=(int, 10 * 1024 * 1024),  # 10MB
    MIN_IMAGE_DIMENSION=(int, 100),
)

# Read the .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool('DEBUG', default=True)

# Allowed Hosts & CSRF Trusted Origins
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://127.0.0.1", "http://localhost"])
CORS_ALLOWED_ORIGIN_REGEXES = [env("CORS_ALLOWED_ORIGIN_REGEXES", default=r"^https:\/\/.*\.ngrok-free\.app$")]

# Authentication
LOGIN_REDIRECT_URL = env("LOGIN_REDIRECT_URL", default="apps:app_list")
LOGIN_URL = env("LOGIN_URL", default="login")

# Email Configuration
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")



# YouTube API
API = env("API")
YOUTUBE_API_VERSION = env("YOUTUBE_API_VERSION", default="v3")
YOUTUBE_API_SERVICE_NAME = env("YOUTUBE_API_SERVICE_NAME", default="youtube")

# CKEditor
CKEDITOR_UPLOAD_PATH = env("CKEDITOR_UPLOAD_PATH", default="uploads/ckeditor/")

# Gemini API
GEMINI_API_KEY = env("GEMINI_API_KEY")

# Pesapal API
PESAPAL_ENVIRONMENT = env("PESAPAL_ENVIRONMENT", default="sandbox")
PESAPAL_CONSUMER_KEY = env("PESAPAL_CONSUMER_KEY")
PESAPAL_CONSUMER_SECRET = env("PESAPAL_CONSUMER_SECRET")
PESAPAL_CALLBACK_URL = env("PESAPAL_CALLBACK_URL")
PESAPAL_IPN_URL = env("PESAPAL_IPN_URL")

# Download Settings
DOWNLOAD_SETTINGS = {
    'MAX_DOWNLOADS': env.int("MAX_DOWNLOADS", default=2),
    'LINK_EXPIRY_HOURS': env.int("LINK_EXPIRY_HOURS", default=24),
    'ENABLE_IP_RESTRICTION': env.bool("ENABLE_IP_RESTRICTION", default=True),
}


GOOGLE_DRIVE_SETTINGS = {
    'SERVICE_ACCOUNT_FILE': os.path.join(GOOGLE_DIR, "django-drive-integration-d57fef033ddb.json"),
    'SCOPES': ['https://www.googleapis.com/auth/drive.file'],
    'API_VERSION': 'v3'
}



# Session & Security Settings
SESSION_TIMEOUT = env.int("SESSION_TIMEOUT")
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD")
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF")
SECURE_BROWSER_XSS_FILTER = env.bool("SECURE_BROWSER_XSS_FILTER")
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS")

# Image Upload Settings
ALLOWED_IMAGE_TYPES = set(env.list("ALLOWED_IMAGE_TYPES", default=["image/jpeg", "image/png", "image/tiff", "image/bmp"]))
MAX_IMAGE_SIZE = env.int("MAX_IMAGE_SIZE")
MIN_IMAGE_DIMENSION = env.int("MIN_IMAGE_DIMENSION")

# Tracked & Excluded URLs
TRACK_URLS = [rf"^{url}" for url in env.list("TRACK_URLS", default=[])]
EXCLUDE_URLS = [rf"^{url}" for url in env.list("EXCLUDE_URLS", default=[])]

# Static & Media Files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = env("MEDIA_URL", default="media/")
MEDIA_ROOT = os.path.join(BASE_DIR, env("MEDIA_ROOT", default="media"))


# CKEditor Configuration
CKEDITOR_CONFIGS = json.loads(env("CKEDITOR_CONFIGS", default='{}'))

# Django Message Tags
MESSAGE_TAGS_ENV = json.loads(env("MESSAGE_TAGS", default="{}"))
MESSAGE_TAGS = {
    messages.ERROR: MESSAGE_TAGS_ENV.get("ERROR", "danger"),
    messages.SUCCESS: MESSAGE_TAGS_ENV.get("SUCCESS", "success"),
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.apps.AppsConfig',
    'users.apps.UsersConfig',
    'ProAir.apps.ProairConfig',
    'ckeditor',
    'ckeditor_uploader',
    'phonenumber_field',
 
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'users.middleware.UserActivityMiddleware',
    'ProAir.middleware.NotificationMiddleware',
   
]



ROOT_URLCONF = 'AirNation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR,'/templates'],
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

WSGI_APPLICATION = 'AirNation.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL='users.CustomUser'

LOGIN_REDIRECT_URL='apps:app_list'
LOGIN_URL='login'


#EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"


# Database configuration for Heroku
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),  # Fallback to SQLite if DATABASE_URL is missing
        conn_max_age=600,  # Optional: Improves performance by reusing database connections
    )
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',  # Identifier for this cache
    }
}


django_heroku.settings(locals())