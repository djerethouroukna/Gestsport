import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from users.models import User
from reservations.models import Reservation, ReservationStatus
from terrains.models import Terrain
from datetime import datetime, timedelta
from decimal import Decimal

print("=== CRÉATION NOUVELLE RÉSERVATION TEST ===")

coach = User.objects.get(email='coachtest@example.com')
terrain = Terrain.objects.first()

# Créer une réservation confirmée
reservation = Reservation.objects.create(
    user=coach,
    terrain=terrain,
    start_time=datetime.now() + timedelta(days=1),
    end_time=datetime.now() + timedelta(days=1, hours=2),
    status=ReservationStatus.CONFIRMED,
    total_amount=Decimal('10000.00'),
    confirmation_date=timezone.now()
)

print(f"✅ Nouvelle réservation créée: {reservation.id}")
print(f"   URL: http://127.0.0.1:8000/reservations/{reservation.id}/")
print(f"   Status: {reservation.status}")
print(f"   Connectez-vous avec: {coach.email}")
print(f"   Bouton paiement devrait être visible !")
