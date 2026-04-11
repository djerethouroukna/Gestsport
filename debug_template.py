#!/usr/bin/env python
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import get_template
from django.template import Context

# Test de chargement du template
try:
    template = get_template('activities/reservation_form.html')
    print(f"✅ Template trouvé: {template.origin}")
    
    # Test de rendu simple
    context = Context({'activity': {'title': 'TEST', 'id': 42}})
    rendered = template.render(context)
    print(f"✅ Template rendu avec succès, longueur: {len(rendered)}")
    
    # Vérifier si DEBUG est présent
    if 'DEBUG: Template activities/reservation_form.html' in rendered:
        print("✅ Marqueur DEBUG trouvé dans le rendu")
    else:
        print("❌ Marqueur DEBUG NON trouvé dans le rendu")
        
except Exception as e:
    print(f"❌ Erreur: {e}")

# Test de l'autre template
try:
    template2 = get_template('reservations/reservation_from_activity.html')
    print(f"✅ Template 2 trouvé: {template2.origin}")
except Exception as e:
    print(f"❌ Template 2 erreur: {e}")
