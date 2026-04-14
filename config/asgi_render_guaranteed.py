"""
ASGI config for GestSport project with guaranteed settings.
"""

import os

from django.core.asgi import get_asgi_application

# Forcer l'utilisation des settings garantis pour Render
if 'RENDER' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_render_guaranteed')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_render_guaranteed')

application = get_asgi_application()
