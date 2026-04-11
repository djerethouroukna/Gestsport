import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from payments.models import Payment

print("=== DEBUG PAYMENT RELATION ===")

res7 = Reservation.objects.get(id=7)
print(f"Réservation 7:")
print(f"  hasattr(res7, 'payment'): {hasattr(res7, 'payment')}")

if hasattr(res7, 'payment'):
    try:
        payment = res7.payment
        print(f"  res7.payment: {payment}")
        print(f"  payment is None: {payment is None}")
    except Exception as e:
        print(f"  Erreur accès payment: {e}")

# Vérifier directement depuis Payment
payment = Payment.objects.filter(reservation=res7).first()
print(f"\nPayment direct:")
print(f"  Payment trouvé: {payment is not None}")
if payment:
    print(f"  Payment.id: {payment.id}")
    print(f"  Payment.status: {payment.status}")
    print(f"  Payment.reservation: {payment.reservation.id}")

# Forcer la relation
print(f"\nTest forcer la relation:")
try:
    res7_with_payment = Reservation.objects.select_related('payment').get(id=7)
    print(f"  select_related payment: {hasattr(res7_with_payment, 'payment')}")
    if hasattr(res7_with_payment, 'payment'):
        print(f"  payment value: {res7_with_payment.payment}")
except Exception as e:
    print(f"  Erreur: {e}")
