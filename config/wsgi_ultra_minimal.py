"""
WSGI config for GestSport project - ULTRA-MINIMAL.
"""

import os

from django.core.wsgi import get_wsgi_application

# Forcer l'utilisation des settings ultra-minimal pour Render
if 'RENDER' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_ultra_minimal')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
