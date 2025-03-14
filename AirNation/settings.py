"""
Django settings for AirNation project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from decouple import config
from django.contrib.messages import constants as messages




# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

GOOGLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SECRET_KEY = 'django-insecure-5lqd&c*w5r6gy8oyjl(jm@9#)qgzytxr7)$#n+un)mdnju2%jw'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.ngrok-free.app','airnation-a64facd01b23.herokuapp.com','51.20.91.33']


CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/.*\.ngrok-free\.app$"
]

# ngrok config add-authtoken 2sJlNuRSFn1F6oGykB02CV476TS_3nMLW8BfNUnE6T2xZkqjQ

CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1","http://localhost","https://*.ngrok-free.app"]





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
    'storages'
 
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # PostgreSQL database engine
        'NAME': 'database-1',  # Replace with your actual database name
        'USER': 'ProAir',  # Master username
        'PASSWORD': 'NrwpAbcu85rWK83D%RAY',  # Master password
        'HOST': 'database-1.cjg6ckkasyvs.eu-north-1.rds.amazonaws.com',  # RDS endpoint
        'PORT': '5432',  # Default PostgreSQL port
    }
}

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

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Change this to a different directory
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = 'media/'
MEDIA_ROOT=os.path.join(BASE_DIR, 'media')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL='users.CustomUser'

LOGIN_REDIRECT_URL='apps:app_list'
LOGIN_URL='login'


EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
#EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST='smtp.gmail.com'
EMAIL_USE_TLS=True
EMAIL_PORT=587
EMAIL_HOST_USER='petrosofteng@gmail.com'
EMAIL_HOST_PASSWORD='latw eilf yckv dwll'


# settings.py

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/tiff', 'image/bmp'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_IMAGE_DIMENSION = 100

# Track specific URLs (optional)
TRACK_URLS = [
    r'^/admin/',
    r'^/accounts/', 
    r'^/manage/',
    r'^/practicals/', 
    r'^/documents/',
    r'^/programs/', 
    r'^/groups/', 
    r'^/vote/', 
    r'^/quiz/', 
    r'^/experience/', 
    r'^/ckeditor/', 
    r'^/new-admin/', 
    r'^/static/',
    r'^/media/',
]

EXCLUDE_URLS = [
    r'^/favicon.ico',
]

# Minimum time (seconds) to consider as a new session
SESSION_TIMEOUT = 30 * 60  # 30 minutes


API="AIzaSyCJFxvWMfN5JORXyZ5POrrJK7kevivapmQ"
YOUTUBE_API_VERSION='v3'
YOUTUBE_API_SERVICE_NAME='youtube'



CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['TextColor', 'BGColor'],  # Add color options
            ['NumberedList', 'BulletedList', 'Outdent', 'Indent'],
            ['RemoveFormat']  # Removed 'Link', 'Unlink', 'Source'
        ],
        'removePlugins': 'image, uploadfile',  # Continue removing unwanted plugins
        'allowedContent': True,
    }
}

#EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"


# Database configuration for Heroku
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'd79qhncilddje0',
        'USER': 'ud9vt3vci0ovvm',
        'PASSWORD': 'pcce9aee1e13b9f670a2af12368210491688919824c6466059882b55201cc59ad',
        'HOST': 'cb5ajfjosdpmil.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',  # Identifier for this cache
    }
}


# AWS settings
AWS_ACCESS_KEY_ID ="AKIARSU7LB224JMD5D24"
AWS_SECRET_ACCESS_KEY = "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"
AWS_STORAGE_BUCKET_NAME = "airnationmusic"
AWS_S3_SIGNATURE_NAME ="s3v4"
AWS_S3_REGION_NAME ="eu-north-1"
AWS_S3_FILE_OVERWRITE =False
AWS_DEFAULT_ACL =None
AWS_S3_VERIFY = True
DEFAULT_FILE_STORAGE="storages.backends.s3boto3.S3Boto3Storage"



CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"


GEMINI_API_KEY = "AIzaSyBnI43Q5_7FA_3b2gxBzw64pcp0O0YRaE0"


# Google Drive API Settings
GOOGLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOOGLE_DRIVE_SETTINGS = {
    'SERVICE_ACCOUNT_FILE':os.path.join(GOOGLE_DIR, "django-drive-integration-d57fef033ddb.json"),
    'SCOPES': ['https://www.googleapis.com/auth/drive.file'],
    'API_VERSION': 'v3'
}

# Download Settings
DOWNLOAD_SETTINGS = {
    'MAX_DOWNLOADS': 2,
    'LINK_EXPIRY_HOURS': 24,
    'ENABLE_IP_RESTRICTION': True,


}


PESAPAL_ENVIRONMENT = "sandbox"  # or "live"
PESAPAL_CONSUMER_KEY = "lddtCViKVHv3jUELMaos80cYSu1SrBuA"
PESAPAL_CONSUMER_SECRET ="CTSGifWt96cy0Q4RXEFWVTpblWE="
PESAPAL_CALLBACK_URL = "https://e594-196-44-160-11.ngrok-free.app/payment/callback/"
PESAPAL_IPN_URL = "https://e594-196-44-160-11.ngrok-free.app/payment/ipn/"



from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
}
