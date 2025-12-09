"""
Django settings optimizado para NUAM - PostgreSQL en Render

CONFIGURACIÓN PARA PRODUCCIÓN:
- PostgreSQL como base de datos principal
- Firebase Storage para documentos PDF
- Celery + Redis para tareas asíncronas
- Seguridad reforzada
- Variables de entorno con python-decouple

INSTRUCCIONES:
1. Renombrar este archivo a settings.py (backup del actual primero)
2. Crear archivo .env en la raíz con las variables requeridas
3. En Render, configurar las variables de entorno en el dashboard
"""

import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-CHANGE-ME-IN-PRODUCTION')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Hosts permitidos
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


# ==============================================================================
# APLICACIONES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    # Apps de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps de terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    # NOTA: Celery comentado - agregar después con Redis/Upstash
    # 'django_celery_beat',
    # 'django_celery_results',

    # Apps del proyecto NUAM
    'usuarios',
    'calificaciones',
    'auditoria',
    'documentos',
]

# Configuración de Crispy Forms (Bootstrap 5)
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para archivos estáticos en producción
    'corsheaders.middleware.CorsMiddleware',       # CORS para API
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nuam_config.urls'


# ==============================================================================
# TEMPLATES
# ==============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Carpeta global de templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Context processor personalizado para el menú
                'nuam_config.context_processors.user_role_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'nuam_config.wsgi.application'


# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS - POSTGRESQL
# ==============================================================================

DATABASES = {
   'default': dj_database_url.config(
       default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),
       conn_max_age=600,
       conn_health_checks=True,
       ssl_require=True,  # Render requiere SSL fuera de la red privada, internamente lo maneja
   )
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nuam_db2',
        'USER': 'postgres',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Configuración adicional de PostgreSQL
#DATABASES['default']['OPTIONS'] = {
#    'options': '-c search_path=public',
#}

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'usuarios.User'


# ==============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================

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


# ==============================================================================
# INTERNACIONALIZACIÓN
# ==============================================================================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# ==============================================================================
# ARCHIVOS ESTÁTICOS (CSS, JavaScript, Images)
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Directorios adicionales para archivos estáticos
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Almacenamiento de archivos estáticos con WhiteNoise (compresión y caché)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ==============================================================================
# ARCHIVOS DE MEDIA (Uploads de usuarios)
# ==============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN
# ==============================================================================

if not DEBUG:
    # HTTPS
    #SECURE_SSL_REDIRECT = True
    #SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Cookies seguras
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Otros headers de seguridad
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

    # Timeouts de sesión
    SESSION_COOKIE_AGE = 3600  # 1 hora
    SESSION_SAVE_EVERY_REQUEST = True
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Content Security Policy (CSP)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://code.jquery.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "https:")


# ==============================================================================
# CONFIGURACIÓN DE DJANGO REST FRAMEWORK
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}

# Configuración de JWT
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# ==============================================================================
# CONFIGURACIÓN DE CORS
# ==============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True


# ==============================================================================
# CONFIGURACIÓN DE CELERY (Tareas Asíncronas)
# ==============================================================================
# NOTA: Comentado temporalmente - descomentar cuando agregues Redis/Upstash

# CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
# CELERY_RESULT_BACKEND = 'django-db'  # Almacenar resultados en PostgreSQL
# CELERY_CACHE_BACKEND = 'default'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = TIME_ZONE
# CELERY_TASK_TRACK_STARTED = True
# CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos máximo por tarea

# Configuración de Celery Beat (Tareas programadas)
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


# ==============================================================================
# CONFIGURACIÓN DE FIREBASE (Storage para PDFs)
# ==============================================================================

FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default=None)
FIREBASE_STORAGE_BUCKET = config('FIREBASE_STORAGE_BUCKET', default='nuam-documentos.appspot.com')

# Si las credenciales están en variable de entorno (JSON string)
FIREBASE_CREDENTIALS_JSON = config('FIREBASE_CREDENTIALS_JSON', default=None)


# ==============================================================================
# CONFIGURACIÓN DE TESSERACT OCR
# ==============================================================================

TESSERACT_CMD = config('TESSERACT_CMD', default='/usr/bin/tesseract')
TESSERACT_LANG = 'spa'  # Idioma español
TESSERACT_CONFIG = '--psm 6 --oem 3'  # PSM: Assume uniform block of text, OEM: LSTM only


# ==============================================================================
# CONFIGURACIÓN DE LOGGING
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file_security'],
            'level': 'WARNING',
            'propagate': False,
        },
        'usuarios': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'calificaciones': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'auditoria': {
            'handlers': ['console', 'file', 'file_security'],
            'level': 'INFO',
            'propagate': False,
        },
        'documentos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}


# ==============================================================================
# CONFIGURACIÓN DE CACHÉ
# ==============================================================================
# NOTA: Redis comentado - usando caché en memoria temporalmente
# Descomentar Redis cuando agregues Upstash

CACHES = {
    'default': {
        # Caché en memoria (temporal - sin Redis)
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',

        # Redis (descomentar cuando agregues Upstash)
        # 'BACKEND': 'django_redis.cache.RedisCache',
        # 'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        # 'OPTIONS': {
        #     'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        #     'PARSER_CLASS': 'redis.connection.HiredisParser',
        #     'PICKLE_VERSION': -1,
        # },
        # 'KEY_PREFIX': 'nuam',
        # 'TIMEOUT': 300,  # 5 minutos por defecto
    }
}


# ==============================================================================
# CONFIGURACIÓN DE EMAIL (Para notificaciones y recuperación de contraseña)
# ==============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@nuam.cl')


# ==============================================================================
# CONFIGURACIÓN DE CIFRADO (django-cryptography)
# ==============================================================================

# Clave de cifrado para datos sensibles (RUT, teléfono, email)
# DEBE ser diferente de SECRET_KEY
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=None)


# ==============================================================================
# CONFIGURACIÓN DE DJANGO-AXES (Límite de intentos de login)
# ==============================================================================
# NOTA: Comentado - agregar después cuando instales django-axes

# Bloquear después de 5 intentos fallidos
# AXES_FAILURE_LIMIT = 5

# Cooldown de 30 minutos
# AXES_COOLOFF_TIME = timedelta(minutes=30)

# Bloquear por combinación de usuario + IP
# AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True

# Usar caché para almacenar intentos
# AXES_CACHE = 'default'

# Solo bloquear intentos del admin y login
# AXES_ONLY_ADMIN_SITE = False


# ==============================================================================
# CONFIGURACIÓN ADICIONAL
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Tamaño máximo de upload (100 MB para PDFs grandes)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB

# Número máximo de campos en POST (para carga masiva)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000


# ==============================================================================
# CONFIGURACIÓN DE DESARROLLO LOCAL
# ==============================================================================

if DEBUG:
    # Mostrar toolbar de debug solo en desarrollo
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

    # IPs permitidas para debug toolbar
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

    # Email a consola en desarrollo
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ==============================================================================
# CREAR CARPETAS NECESARIAS
# ==============================================================================

# Crear carpeta de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Crear carpeta de media si no existe
MEDIA_ROOT_PATH = Path(MEDIA_ROOT)
MEDIA_ROOT_PATH.mkdir(exist_ok=True)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' 

# ==============================================================================
# VARIABLES DE ENTORNO REQUERIDAS PARA RENDER
# ==============================================================================

"""
Configurar estas variables en Render Dashboard:

REQUERIDAS:
- SECRET_KEY: Clave secreta de Django (generar con: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
- DATABASE_URL: URL de PostgreSQL (automática en Render)
- ALLOWED_HOSTS: Dominios permitidos (ej: nuam.onrender.com,www.nuam.cl)

OPCIONALES:
- DEBUG: False (en producción)
- REDIS_URL: URL de Redis para Celery (ej: redis://red-xxxxx:6379/0)
- FIREBASE_CREDENTIALS_JSON: JSON con credenciales de Firebase
- FIREBASE_STORAGE_BUCKET: Nombre del bucket de Firebase Storage
- EMAIL_HOST_USER: Email para envío de notificaciones
- EMAIL_HOST_PASSWORD: Contraseña del email
- FIELD_ENCRYPTION_KEY: Clave para cifrado de campos sensibles
- CORS_ALLOWED_ORIGINS: Orígenes permitidos para CORS

RENDER ESPECÍFICAS:
- PYTHON_VERSION: 3.11.0
- BUILD_COMMAND: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
- START_COMMAND: gunicorn nuam_config.wsgi:application
"""
