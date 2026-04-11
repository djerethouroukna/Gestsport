import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from payments.models import Payment, PaymentStatus
from reservations.models import Reservation

print("=== SIMULATION PAIEMENT RÉUSSI ===")

# Récupérer la réservation 13
reservation = Reservation.objects.get(id=13)
payment = Payment.objects.filter(reservation=reservation).first()

print(f"Avant simulation:")
print(f"  Payment status: {payment.status}")
print(f"  Reservation status: {reservation.status}")
print(f"  Reservation is_paid: {reservation.is_paid}")

# Simuler un paiement réussi
payment.status = 'paid'
payment.paid_at = timezone.now()
# Ne pas mettre de transaction_id simulé (laisser None)
payment.save()

print(f"\n✅ Paiement simulé comme réussi:")
print(f"  Payment status: {payment.status}")
print(f"  Transaction ID: {payment.transaction_id}")
print(f"  Paid at: {payment.paid_at}")

# Vérifier l'impact sur la réservation
reservation.refresh_from_db()
print(f"\nImpact sur la réservation:")
print(f"  Reservation status: {reservation.status}")
print(f"  Reservation is_paid: {reservation.is_paid}")
print(f"  Reservation payment_status: {reservation.payment_status}")

print(f"\n=== ÉTATS ATTENDUS POUR LES BOUTONS ===")

# État pour l'admin
print(f"\n🔵 ADMIN (réservation 13):")
if reservation.status == 'pending' and reservation.is_paid:
    print(f"  ✅ Bouton 'Confirmer la Réservation': VISIBLE")
    print(f"  ✅ Bouton 'Rejeter la Réservation': VISIBLE")
else:
    print(f"  ❌ Bouton 'Confirmer la Réservation': NON VISIBLE")
    print(f"  ✅ Bouton 'Rejeter la Réservation': VISIBLE")

# État pour le coach
print(f"\n🟢 COACH (réservation 13):")
if reservation.status == 'pending' and reservation.is_paid:
    print(f"  ❌ Bouton 'Procéder au Paiement': NON VISIBLE (déjà payé)")
    print(f"  ❌ Bouton 'Générer le Ticket': NON VISIBLE (en attente confirmation admin)")
elif reservation.status == 'confirmed' and reservation.is_paid:
    print(f"  ❌ Bouton 'Procéder au Paiement': NON VISIBLE")
    print(f"  ✅ Bouton 'Générer le Ticket': VISIBLE")
    print(f"  ❌ Bouton 'Télécharger le Ticket': NON VISIBLE (pas encore généré)")
else:
    print(f"  ❌ Aucun bouton de ticket visible")

print(f"\n=== INSTRUCTIONS POUR TESTER ===")
print(f"1. Connectez-vous en tant qu'ADMIN")
print(f"2. Allez sur: http://127.0.0.1:8000/reservations/13/")
print(f"3. Vous devriez voir le bouton 'Confirmer la Réservation'")
print(f"4. Cliquez sur 'Confirmer la Réservation'")
print(f"5. Après confirmation, reconnectez-vous en tant que COACH")
print(f"6. Allez sur: http://127.0.0.1:8000/reservations/13/")
print(f"7. Vous devriez voir le bouton 'Générer le Ticket'")

print(f"\n=== URLS DE TEST ===")
print(f"Admin: http://127.0.0.1:8000/admin/")
print(f"Réservation: http://127.0.0.1:8000/reservations/13/")

# Créer un admin de test si nécessaire
from users.models import User
admin_users = User.objects.filter(role='admin')
if not admin_users.exists():
    print(f"\n⚠️  Aucun admin trouvé. Création d'un admin de test...")
    admin = User.objects.create_user(
        email='admin@example.com',
        password='adminpass123',
        role='admin',
        first_name='Admin',
        last_name='Test',
        is_staff=True,
        is_superuser=True
    )
    print(f"✅ Admin créé: admin@example.com / adminpass123")
else:
    admin = admin_users.first()
    print(f"\n✅ Admin existant: {admin.email}")

print(f"\n=== COMPES DE TEST ===")
print(f"Coach: coachtest@example.com / coachpass123")
print(f"Admin: {admin.email} / adminpass123")
