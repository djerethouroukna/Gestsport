from payments.models import Payment
from reservations.models import Reservation
from django.utils import timezone

print("=== CORRECTION DES PAIEMENTS ===")
paid_payments = Payment.objects.filter(status='paid')
print('Paiements en statut paid:', paid_payments.count())

corrected = 0
for payment in paid_payments:
    try:
        if payment.reservation and payment.reservation.status == 'completed':
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.save()
            corrected += 1
            print('Paiement corrige:', str(payment.id)[:8], '...')
        else:
            print('Non corrige - statut reservation:', payment.reservation.status if payment.reservation else 'N/A')
    except Exception as e:
        print('Erreur:', e)

print('Corriges:', corrected)
print('Restants en paid:', Payment.objects.filter(status='paid').count())
print('Nouveaux completed:', Payment.objects.filter(status='completed').count())
