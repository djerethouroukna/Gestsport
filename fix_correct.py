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
            print(f'✅ Paiement {str(payment.id)[:8]}... corrige: paid -> completed (reservation completed)')
        else:
            print(f'⏸️  Paiement {str(payment.id)[:8]}... - Reservation statut: {payment.reservation.status if payment.reservation else "N/A"}')
    except Exception as e:
        print(f'❌ Erreur avec paiement {payment.id}: {e}')

print(f'\n🎯 Résultat:')
print(f'   ✅ Corriges: {corrected}')
print(f'   📊 Restants en paid: {Payment.objects.filter(status="paid").count()}')
print(f'   ✅ Nouveaux completed: {Payment.objects.filter(status="completed").count()}')

print('\n=== VERIFICATION ===')
total_completed = Payment.objects.filter(status='completed').count()
total_paid = Payment.objects.filter(status='paid').count()
print(f'Total completed: {total_completed}')
print(f'Total paid: {total_paid}')
print(f'Total general: {total_completed + total_paid}')
