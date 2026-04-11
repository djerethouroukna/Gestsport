# Script pour nettoyer les paiements en double
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from payments.models import Payment
from reservations.models import Reservation

print("=== NETTOYAGE PAIEMENTS EN DOUBLE ===")

# Vérifier la réservation 19
try:
    reservation = Reservation.objects.get(id=19)
    print(f"Réservation 19:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    print(f"  Has payment: {reservation.has_payment}")
    
    # Vérifier les paiements pour cette réservation
    payments = Payment.objects.filter(reservation=reservation)
    print(f"\nPaiements trouvés: {payments.count()}")
    
    for payment in payments:
        print(f"\nPayment {payment.id}:")
        print(f"  Status: {payment.status}")
        print(f"  Amount: {payment.amount}")
        print(f"  Created: {payment.created_at}")
        print(f"  Notes: {payment.notes}")
    
    # S'il y a plusieurs paiements, supprimer les anciens
    if payments.count() > 1:
        print(f"\n🧹 Nettoyage des anciens paiements...")
        for payment in payments.order_by('-created_at')[1:]:  # Garder le plus récent
            print(f"  Suppression payment {payment.id}")
            payment.delete()
    
    # Vérifier après nettoyage
    remaining_payments = Payment.objects.filter(reservation=reservation)
    print(f"\n✅ Paiements restants: {remaining_payments.count()}")
    
    if remaining_payments.count() == 1:
        payment = remaining_payments.first()
        print(f"  Payment conservé: {payment.id} - {payment.status}")
    
except Reservation.DoesNotExist:
    print(f"❌ Réservation 19 non trouvée")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== VÉRIFICATION AUTRES RÉSERVATIONS ===")

# Vérifier s'il y a d'autres doublons
reservations_with_duplicates = []
all_reservations = Reservation.objects.all()

for reservation in all_reservations:
    payments = Payment.objects.filter(reservation=reservation)
    if payments.count() > 1:
        reservations_with_duplicates.append(reservation.id)
        print(f"⚠️  Réservation {reservation.id}: {payments.count()} paiements")

if reservations_with_duplicates:
    print(f"\n📋 Réservations avec doublons: {reservations_with_duplicates}")
else:
    print(f"\n✅ Aucun autre doublon trouvé")

print(f"\n=== NETTOYAGE TERMINÉ ===")
print(f"1. Réessayez le paiement pour la réservation 19")
print(f"2. Le webhook devrait maintenant fonctionner")
print(f"3. Vérifiez les logs Django")
