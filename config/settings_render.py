"""
Settings pour Render - sans Pillow et autres packages problématiques
"""
from .settings import *

# Désactiver les fonctionnalités qui nécessitent Pillow
PILLOW_ENABLED = False

# Désactiver les QR codes temporairement
QR_CODES_ENABLED = False

# Désactiver le traitement d'images avancé
IMAGE_PROCESSING_ENABLED = False

# Configuration simplifiée pour Render
if 'RENDER' in os.environ:
    # Désactiver les apps qui nécessitent Pillow
    INSTALLED_APPS = [
        app for app in INSTALLED_APPS 
        if app not in [
            'simple_scanner',  # Si elle existe et utilise Pillow
        ]
    ]
    
    # Configuration de logging simplifiée
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

# Configuration des médias sans Pillow
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Désactiver le traitement d'images dans les modèles
THUMBNAIL_ALIASES = {}  # Désactiver easy-thumbnails si utilisé
