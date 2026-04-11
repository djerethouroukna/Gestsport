from payments.models import Payment
from reservations.models import Reservation

print("=== ANALYSE DES STATUTS ===")
paid_payments = Payment.objects.filter(status='paid')
print('Paiements en statut paid:', paid_payments.count())

# Analyser les statuts des réservations associées
status_count = {}
for payment in paid_payments:
    if payment.reservation:
        status = payment.reservation.status
        status_count[status] = status_count.get(status, 0) + 1
        print(f'Paiement {payment.id[:8]}... - Réservation {payment.reservation.id[:8]}... - Statut: {status}')

print('\n=== STATISTIQUES DES STATUTS ===')
for status, count in status_count.items():
    print(f'{status}: {count}')

print('\n=== RÉSERVATIONS CONFIRMÉES ===')
confirmed_reservations = Reservation.objects.filter(status='confirmed')
print(f'Réservations confirmées: {confirmed_reservations.count()}')

for res in confirmed_reservations[:5]:  # Premier 5
    payment = Payment.objects.filter(reservation=res).first()
    payment_status = payment.status if payment else 'N/A'
    print(f'Réservation {res.id[:8]}... - Paiement: {payment_status}')
