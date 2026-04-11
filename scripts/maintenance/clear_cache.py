import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loaders import cached
from django.conf import settings

print('Template engines:')
for engine in settings.TEMPLATES:
    print(f'  - {engine["BACKEND"]}')
    if 'OPTIONS' in engine:
        print(f'    Options: {engine["OPTIONS"]}')

# Vider le cache de templates
try:
    from django.core.cache import cache
    cache.clear()
    print('\nCache Django vidé')
except Exception as e:
    print(f'\nErreur vidant cache: {e}')
