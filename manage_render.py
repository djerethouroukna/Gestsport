#!/usr/bin/env python
"""Django's command-line utility for administrative tasks with guaranteed settings."""
import os
import sys

# Forcer l'utilisation des settings garantis pour Render
if 'RENDER' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_render_guaranteed')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc

if __name__ == '__main__':
    execute_from_command_line(sys.argv)
