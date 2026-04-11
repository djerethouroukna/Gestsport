import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from payments.models import Payment

print("=== TEST RÉSERVATION COACH ===")

# Réservation 6 (non payée)
res6 = Reservation.objects.get(id=6)
print(f"Réservation 6:")
print(f"  User: {res6.user.username}")
print(f"  Status: {res6.status}")
print(f"  Is paid: {res6.is_paid}")
print(f"  → Bouton paiement: {res6.status == 'confirmed' and not res6.is_paid}")

# Réservation 7 (devrait être payée)
res7 = Reservation.objects.get(id=7)
print(f"\nRéservation 7:")
print(f"  User: {res7.user.username}")
print(f"  Status: {res7.status}")
print(f"  Is paid: {res7.is_paid}")
print(f"  → Bouton ticket: {res7.status == 'confirmed' and res7.is_paid and not hasattr(res7, 'ticket')}")

# Vérifier le payment
payment = Payment.objects.filter(reservation=res7).first()
print(f"\nPayment pour réservation 7:")
if payment:
    print(f"  ID: {payment.id}")
    print(f"  Status: {payment.status}")
    print(f"  Amount: {payment.amount}")
else:
    print("  Aucun payment trouvé")

print("\n=== URLS DE TEST ===")
print("1. Connectez-vous avec le coach: None")
print("2. Test paiement: http://127.0.0.1:8000/reservations/6/")
print("3. Test ticket: http://127.0.0.1:8000/reservations/7/")
