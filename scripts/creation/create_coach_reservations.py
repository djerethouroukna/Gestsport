import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation, ReservationStatus
from terrains.models import Terrain
from users.models import User
from datetime import datetime, timedelta
from decimal import Decimal
from payments.models import Payment

print("=== CRÉATION RÉSERVATIONS COACH RÉELLES ===")

# Trouver un coach réel
coach = User.objects.filter(role='coach').first()
terrain = Terrain.objects.first()

print(f"Coach: {coach.username if coach else 'None'}")
print(f"Terrain: {terrain.name if terrain else 'None'}")

if coach and terrain:
    # Supprimer les anciennes réservations de test
    Reservation.objects.filter(user=coach).delete()
    print("Anciennes réservations supprimées")
    
    # Réservation pour tester le paiement (non payée)
    reservation_paiement = Reservation.objects.create(
        user=coach,
        terrain=terrain,
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=2),
        status=ReservationStatus.CONFIRMED,
        total_amount=Decimal('10000.00')
    )
    print(f"✅ Réservation PAIEMENT créée: {reservation_paiement.id}")
    print(f"   User: {reservation_paiement.user.username}")
    print(f"   Status: {reservation_paiement.status}")
    print(f"   Is paid: {reservation_paiement.is_paid}")
    print(f"   → URL: http://127.0.0.1:8000/reservations/{reservation_paiement.id}/")
    
    # Réservation pour tester le ticket (payée)
    reservation_ticket = Reservation.objects.create(
        user=coach,
        terrain=terrain,
        start_time=datetime.now() + timedelta(days=2),
        end_time=datetime.now() + timedelta(days=2, hours=2),
        status=ReservationStatus.CONFIRMED,
        total_amount=Decimal('10000.00')
    )
    
    # Créer le paiement
    payment = Payment.objects.create(
        reservation=reservation_ticket,
        user=coach,
        amount=Decimal('10000.00'),
        currency='XOF',
        status='paid'
    )
    
    print(f"✅ Réservation TICKET créée: {reservation_ticket.id}")
    print(f"   User: {reservation_ticket.user.username}")
    print(f"   Status: {reservation_ticket.status}")
    print(f"   Is paid: {reservation_ticket.is_paid}")
    print(f"   → URL: http://127.0.0.1:8000/reservations/{reservation_ticket.id}/")
    
    print(f"\n=== INSTRUCTIONS ===")
    print(f"1. Connectez-vous avec: {coach.username}")
    print(f"2. Test paiement: http://127.0.0.1:8000/reservations/{reservation_paiement.id}/")
    print(f"3. Test ticket: http://127.0.0.1:8000/reservations/{reservation_ticket.id}/")
    print(f"4. Les boutons devraient maintenant être fonctionnels !")
else:
    print("❌ Coach ou terrain non trouvé")
