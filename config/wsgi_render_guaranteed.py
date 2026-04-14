"""
WSGI config for GestSport project with guaranteed settings.
"""

import os

from django.core.wsgi import get_wsgi_application

# Forcer l'utilisation des settings garantis pour Render
if 'RENDER' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_render_guaranteed')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
