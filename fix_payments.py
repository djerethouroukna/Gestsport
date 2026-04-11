from payments.models import Payment
from reservations.models import Reservation
from django.utils import timezone

paid_payments = Payment.objects.filter(status='paid')
print(f'Paiements en statut paid: {paid_payments.count()}')

corrected = 0
for payment in paid_payments:
    try:
        if payment.reservation and payment.reservation.status == 'confirmed':
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.save()
            corrected += 1
            print(f'✅ Paiement {payment.id} corrigé')
    except Exception as e:
        print(f'❌ Erreur: {e}')

print(f'Total corrigé: {corrected}')
print(f'Restant en paid: {Payment.objects.filter(status="paid").count()}')
print(f'Nouveaux completed: {Payment.objects.filter(status="completed").count()}')
