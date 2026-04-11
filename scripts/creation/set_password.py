import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from reservations.models import Reservation

User = get_user_model()

# Trouver la réservation 42
try:
    reservation = Reservation.objects.get(id=42)
    user = reservation.user
    print(f'User: {user.email}')
    
    # Définir un mot de passe
    user.set_password('password123')
    user.save()
    print('Mot de passe défini: password123')
    
except Reservation.DoesNotExist:
    print('Reservation ID 42 non trouvee')
except Exception as e:
    print(f'Erreur: {e}')
