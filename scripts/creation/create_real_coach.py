import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from users.models import User
from reservations.models import Reservation, ReservationStatus
from terrains.models import Terrain
from datetime import datetime, timedelta
from decimal import Decimal
from payments.models import Payment

print("=== CRÉATION COACH RÉEL AVEC RÉSERVATIONS ===")

# Créer un coach avec un vrai email
try:
    coach = User.objects.create_user(
        email='coachtest@example.com',
        password='coachpass123',
        role='coach',
        first_name='Coach',
        last_name='Test'
    )
    print(f"✅ Coach créé: {coach.email}")
    print(f"   Email: {coach.email}")
    print(f"   Mot de passe: coachpass123")
except Exception as e:
    print(f"Coach existe déjà ou erreur: {e}")
    coach = User.objects.get(email='coachtest@example.com')

terrain = Terrain.objects.first()

if coach and terrain:
    # Supprimer les anciennes réservations
    Reservation.objects.filter(user=coach).delete()
    
    # Réservation pour paiement
    reservation_paiement = Reservation.objects.create(
        user=coach,
        terrain=terrain,
        start_time=datetime.now() + timedelta(days=1),
        end_time=datetime.now() + timedelta(days=1, hours=2),
        status=ReservationStatus.CONFIRMED,
        total_amount=Decimal('10000.00')
    )
    
    # Réservation pour ticket
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
    
    print(f"\n✅ Réservations créées:")
    print(f"  Paiement: {reservation_paiement.id} - http://127.0.0.1:8000/reservations/{reservation_paiement.id}/")
    print(f"  Ticket: {reservation_ticket.id} - http://127.0.0.1:8000/reservations/{reservation_ticket.id}/")
    
    print(f"\n=== INSTRUCTIONS FINALES ===")
    print(f"1. Connectez-vous avec: coachtest@example.com / coachpass123")
    print(f"2. Allez sur: http://127.0.0.1:8000/reservations/{reservation_paiement.id}/")
    print(f"3. Cliquez sur 'Procéder au Paiement'")
    print(f"4. Allez sur: http://127.0.0.1:8000/reservations/{reservation_ticket.id}/")
    print(f"5. Cliquez sur 'Générer le Ticket'")
    print(f"6. Les boutons devraient maintenant être FONCTIONNELS !")
    
else:
    print("❌ Coach ou terrain non trouvé")
