import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation

print("=== DEBUG IS_PAID ===")

res7 = Reservation.objects.select_related('payment').get(id=7)
print(f"Réservation 7:")
print(f"  has_payment: {res7.has_payment}")
print(f"  payment: {res7.payment}")
print(f"  payment.is_paid: {res7.payment.is_paid if res7.payment else 'None'}")
print(f"  is_paid: {res7.is_paid}")

# Vérifier le statut exact
if res7.payment:
    print(f"\nPayment details:")
    print(f"  status: '{res7.payment.status}'")
    print(f"  is_paid method: {res7.payment.is_paid}")
    print(f"  status == 'paid': {res7.payment.status == 'paid'}")
    
    # Vérifier la méthode is_paid du Payment
    print(f"\nPayment.is_paid method:")
    print(f"  hasattr(payment, 'is_paid'): {hasattr(res7.payment, 'is_paid')}")
    if hasattr(res7.payment, 'is_paid'):
        print(f"  payment.is_paid(): {res7.payment.is_paid()}")
