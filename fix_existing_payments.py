from payments.models import Payment
from reservations.models import Reservation
from django.utils import timezone

# Récupérer tous les paiements en statut 'paid'
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
            print(f'✅ Paiement {payment.id} (réservation {payment.reservation.id}) corrigé: paid → completed')
        else:
            print(f'⏸️  Paiement {payment.id} - Réservation {payment.reservation.id if payment.reservation else "N/A"} statut: {payment.reservation.status if payment.reservation else "N/A"}')
    except Exception as e:
        print(f'❌ Erreur avec paiement {payment.id}: {e}')

print(f'\n🎯 Résultat:')
print(f'   ✅ Corrigés: {corrected}')
print(f'   📊 Restants en paid: {Payment.objects.filter(status="paid").count()}')
print(f'   ✅ Nouveaux completed: {Payment.objects.filter(status="completed").count()}')
