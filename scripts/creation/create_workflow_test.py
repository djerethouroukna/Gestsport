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
from payments.models import Payment

print("=== CRÉATION WORKFLOW TEST COACH → ADMIN → TICKET ===")

coach = User.objects.get(email='coachtest@example.com')
terrain = Terrain.objects.first()

# Étape 1: Créer une réservation PENDING (non confirmée)
reservation = Reservation.objects.create(
    user=coach,
    terrain=terrain,
    start_time=datetime.now() + timedelta(days=1),
    end_time=datetime.now() + timedelta(days=1, hours=2),
    status=ReservationStatus.PENDING,  # Important: PENDING au début
    total_amount=Decimal('10000.00')
)

print(f"✅ Étape 1 - Réservation créée: {reservation.id}")
print(f"   Status: {reservation.status}")
print(f"   Is paid: {reservation.is_paid}")
print(f"   URL: http://127.0.0.1:8000/reservations/{reservation.id}/")

print(f"\n=== WORKFLOW ATTENDU ===")
print(f"1. COACH: Connectez-vous avec {coach.email}")
print(f"2. COACH: Allez sur http://127.0.0.1:8000/reservations/{reservation.id}/")
print(f"3. COACH: Cliquez sur 'Procéder au Paiement' (réservation est pending)")
print(f"4. COACH: Effectuez le paiement")
print(f"5. ADMIN: Connectez-vous et allez sur la même page")
print(f"6. ADMIN: Cliquez sur 'Confirmer la Réservation' (réservation est payée)")
print(f"7. COACH: Revenez sur la page et cliquez sur 'Générer le Ticket'")

print(f"\n=== ÉTATS DES BOUTONS ===")
print(f"Coach (réservation pending, non payée):")
print(f"  ✅ Bouton paiement: VISIBLE")
print(f"  ❌ Bouton ticket: NON VISIBLE")

print(f"\nAdmin (réservation pending, non payée):")
print(f"  ❌ Bouton confirmer: NON VISIBLE ('En attente de paiement')")
print(f"  ✅ Bouton rejeter: VISIBLE")

print(f"\nAprès paiement du coach:")
print(f"Admin (réservation pending, payée):")
print(f"  ✅ Bouton confirmer: VISIBLE")
print(f"  ✅ Bouton rejeter: VISIBLE")

print(f"\nAprès confirmation de l'admin:")
print(f"Coach (réservation confirmed, payée):")
print(f"  ✅ Bouton ticket: VISIBLE")
print(f"  ❌ Bouton paiement: NON VISIBLE")
