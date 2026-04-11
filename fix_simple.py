from payments.models import Payment
from reservations.models import Reservation
from django.utils import timezone

paid_payments = Payment.objects.filter(status='paid')
print('Paiements en statut paid:', paid_payments.count())

corrected = 0
for payment in paid_payments:
    try:
        if payment.reservation and payment.reservation.status == 'confirmed':
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.save()
            corrected += 1
            print('Paiement', payment.id, 'corrige')
        else:
            print('Paiement', payment.id, 'non corrige - reservation non confirmee')
    except Exception as e:
        print('Erreur:', e)

print('Corriges:', corrected)
print('Restants en paid:', Payment.objects.filter(status='paid').count())
print('Nouveaux completed:', Payment.objects.filter(status='completed').count())
