import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from reservations.models import Reservation

print("=== CONFIRMATION RÉSERVATION 12 ===")

try:
    reservation = Reservation.objects.get(id=12)
    print(f"Réservation 12 actuelle:")
    print(f"  Status: {reservation.status}")
    print(f"  User: {reservation.user.email}")
    
    # Confirmer la réservation
    reservation.status = 'confirmed'
    reservation.confirmation_date = timezone.now()
    reservation.save()
    
    print(f"\n✅ Réservation 12 confirmée:")
    print(f"  Nouveau status: {reservation.status}")
    print(f"  URL: http://127.0.0.1:8000/reservations/12/")
    print(f"  Connectez-vous avec: {reservation.user.email}")
    print(f"  Le bouton 'Procéder au Paiement' devrait maintenant apparaître !")
    
except Reservation.DoesNotExist:
    print("❌ Réservation 12 n'existe pas")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
