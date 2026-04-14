"""
Settings minimal pour Render - GARANTIT l'affichage du projet
"""
from .settings import *

# Désactiver TOUTES les fonctionnalités non essentielles
PILLOW_ENABLED = False
QR_CODES_ENABLED = False
IMAGE_PROCESSING_ENABLED = False
PDF_GENERATION_ENABLED = False
TICKETS_ENABLED = False
NOTIFICATIONS_ENABLED = False
CHAT_ENABLED = False
PAYMENTS_ENABLED = False

# Apps minimales uniquement
MINIMAL_INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'channels',
    'users',
    'terrains',
    'events',
    'activities',
    'reservations',
]

# Configuration pour Render
if 'RENDER' in os.environ:
    DEBUG = False
    ALLOWED_HOSTS = ['*']
    
    # Utiliser les apps minimales
    INSTALLED_APPS = MINIMAL_INSTALLED_APPS
    
    # Base de données PostgreSQL
    DATABASES = {
        'default': dj_database_url.parse(config('DATABASE_URL'))
    }
    
    # Cache Redis
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': config('REDIS_URL'),
        }
    }
    
    # Configuration simplifiée
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
    
    # Logging simple
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    }

# Désactiver les features non essentielles
if not getattr(settings, 'PDF_GENERATION_ENABLED', False):
    # Désactiver ReportLab
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'reportlab' not in app.lower()]

if not getattr(settings, 'TICKETS_ENABLED', False):
    # Désactiver les tickets
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'tickets' not in app.lower()]

if not getattr(settings, 'CHAT_ENABLED', False):
    # Désactiver le chat
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'chat' not in app.lower()]

if not getattr(settings, 'NOTIFICATIONS_ENABLED', False):
    # Désactiver les notifications
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'notifications' not in app.lower()]

if not getattr(settings, 'PAYMENTS_ENABLED', False):
    # Désactiver les paiements
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'payments' not in app.lower()]

# Configuration des URLs minimales
MINIMAL_URLS = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('terrains.urls')),
    path('api/', include('events.urls')),
    path('api/', include('activities.urls')),
    path('api/', include('reservations.urls')),
    path('health/', 'config.health.health_check', name='health-check'),
]

# Utiliser les URLs minimales si en mode minimal
if 'RENDER' in os.environ and not getattr(settings, 'FULL_FEATURES_ENABLED', False):
    urlpatterns = MINIMAL_URLS
