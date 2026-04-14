"""
WSGI config for GestSport project - SANS Pillow.
"""

import os

from django.core.wsgi import get_wsgi_application

# Forcer l'utilisation des settings sans Pillow pour Render
if 'RENDER' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_no_pillow')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
