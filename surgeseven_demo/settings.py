"""
Django settings for surgeseven_demo project.
"""

import cloudinary
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from datetime import timedelta
import redis
from urllib.parse import urlparse
from decouple import config


load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7*p9vc)2sy2vn&e0t6uph-^ycs7+(gzw$3-p+bw0@%df(hyuyb'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "surgeseven-demo.onrender.com", "www.surgesevenltd.com", "127.0.0.1"]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'users',
    'subscriptions',
    'booking',
    'payment',
    'delivery',
    'dashboard',
    'notifications',
    'tracker',
    'qr_generator',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'storages',
    'cloudinary',
    'cloudinary_storage',
    'webpush',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'payment.middleware.PaystackIPWhitelistMiddleware',  # Temporarily disabled for development
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'surgeseven_demo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notifications',
                'notifications.context_processors.vapid_public_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'surgeseven_demo.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
    }
}

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')

# Conditional settings based on DEBUG mode
if not DEBUG:
    # PRODUCTION SETTINGS
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    PAYSTACK_WEBHOOK_URL = 'https://surgesevenltd.com/paystack/webhook/'
    
    # Re-enable middleware in production
    MIDDLEWARE.insert(7, 'payment.middleware.PaystackIPWhitelistMiddleware')
    
else:
    # DEVELOPMENT SETTINGS
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_BROWSER_XSS_FILTER = False
    
    PAYSTACK_WEBHOOK_URL = 'http://localhost:8000/payment/webhook/'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Resend Configuration
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'SurgeSeven adminhr@surgesevenltd.com')
DEFAULT_REPLY_TO_EMAIL = os.getenv('DEFAULT_REPLY_TO_EMAIL', 'adminhr@surgesevenltd.com')

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.resend.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'resend')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', RESEND_API_KEY)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# iTracksafeX Settings
ITRACKSAFE_MASTER_USERNAME = os.getenv("MASTER_TRACKER_USERNAME")
ITRACKSAFE_MASTER_PASSWORD = os.getenv("MASTER_TRACKER_PASSWORD")
ITRACKSAFE_ADMIN_USERNAME = "surgeseven_admin"
ITRACKSAFE_ADMIN_PASSWORD = os.getenv("ADMIN_TRACKER_PASSWORD")
ITRACKSAFE_CLIENT_PREFIX = os.getenv("CLIENT_TRACKER_PASSWORD_PREFIX")
ITRACKSAFE_OWNER_PREFIX = os.getenv("OWNER_TRACKER_PASSWORD_PREFIX")
ITRACKSAFE_API_URL = "https://itracksafe.com/webapi"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv("CLOUD_NAME"),
    'API_KEY': os.getenv("API_KEY"),
    'API_SECRET': os.getenv("API_SECRET"),
    'SECURE': True,
    'MEDIA_TAG': 'surgeseven-media',
    'INVALID_VIDEO_ERROR_MESSAGE': 'Please upload a valid video file',
    'EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS': (),
    'STATIC_TAG': 'surgeseven-static',
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'manifest'),
}

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/'

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": os.getenv("VAPID_PUBLIC_KEY", "").replace('\n', ''),
    "VAPID_PRIVATE_KEY": os.getenv("VAPID_PRIVATE_KEY", "").replace('\n', ''),
    "VAPID_ADMIN_EMAIL": "adminhr@surgesevenltd.com"
}

BASE_URL = "https://surgesevenltd.com"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
    }
}

BARCODE_DEFAULT_REDIRECT = 'https://surgesevenltd.com'
BARCODE_IMAGE_FORMAT = 'PNG'

# QR Code settings
QR_CODE_DEFAULT_REDIRECT = 'https://surgesevenltd.com'
QR_CODE_IMAGE_FORMAT = 'PNG'
QR_CODE_VERSION = 1
QR_CODE_BOX_SIZE = 10
QR_CODE_BORDER = 4
QR_CODE_FILL_COLOR = 'black'
QR_CODE_BACK_COLOR = 'white'

# Site configuration
SITE_URL = 'https://surgesevenltd.com'