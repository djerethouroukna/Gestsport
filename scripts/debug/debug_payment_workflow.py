import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from payments.models import Payment
from users.models import User
from django.core.mail import send_mail
from django.conf import settings

print("=== DIAGNOSTIC WORKFLOW PAIEMENT ===")

# Vérifier toutes les réservations récentes
print("1. RÉSERVATIONS RÉCENTES:")
reservations = Reservation.objects.all().order_by('-created_at')[:5]
for res in reservations:
    print(f"  Réservation {res.id}:")
    print(f"    User: {res.user.email if res.user else 'None'}")
    print(f"    Status: {res.status}")
    print(f"    Is paid: {res.is_paid}")
    print(f"    Payment status: {res.payment_status}")
    print(f"    Created: {res.created_at}")
    
    # Vérifier les paiements
    payments = Payment.objects.filter(reservation=res)
    for payment in payments:
        print(f"    Payment {payment.id}: {payment.status} - {payment.amount} {payment.currency}")

print("\n2. UTILISATEURS ADMIN:")
admins = User.objects.filter(role='admin')
for admin in admins:
    print(f"  Admin: {admin.email} - {admin.get_full_name()}")

print("\n3. CONFIGURATION EMAIL:")
print(f"  Email backend: {settings.EMAIL_BACKEND}")
print(f"  From email: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Non configuré')}")
print(f"  Email host: {getattr(settings, 'EMAIL_HOST', 'Non configuré')}")

print("\n4. TEST ENVOI EMAIL ADMIN:")
try:
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    # Simuler un email de notification
    subject = "Nouveau paiement à confirmer"
    context = {
        'reservation': reservations.first(),
        'user': reservations.first().user if reservations.first() else None,
        'site_name': 'Terrain Manager'
    }
    
    # Message simple
    message = f"""
    Un nouveau paiement a été effectué et nécessite votre confirmation:
    
    Réservation: {reservations.first().id if reservations.first() else 'N/A'}
    Client: {reservations.first().user.email if reservations.first() and reservations.first().user else 'N/A'}
    Montant: {reservations.first().total_amount if reservations.first() else 'N/A'} FCFA
    Statut: Payé en attente de confirmation
    
    Veuillez vous connecter pour confirmer cette réservation.
    """
    
    # Test d'envoi
    sent = send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [admin.email for admin in admins],
        fail_silently=False,
    )
    
    print(f"  ✅ Email envoyé à {sent} admin(s)")
    
except Exception as e:
    print(f"  ❌ Erreur envoi email: {e}")
    import traceback
    traceback.print_exc()

print("\n5. VÉRIFICATION WEBHOOK STRIPE:")
print(f"  Stripe webhook secret: {'Configuré' if getattr(settings, 'STRIPE_WEBHOOK_SECRET', None) else 'NON CONFIGURÉ'}")
print(f"  Webhook URL: http://127.0.0.1:8000/payments/stripe/webhook/")

print("\n6. PAIEMENTS EN ATTENTE:")
pending_payments = Payment.objects.filter(status='pending')
print(f"  Paiements pending: {pending_payments.count()}")
for payment in pending_payments:
    print(f"    Payment {payment.id}: {payment.amount} {payment.currency}")
    print(f"    Réservation: {payment.reservation.id}")
    print(f"    User: {payment.user.email}")

print("\n7. RÉSERVATIONS PAYÉES NON CONFIRMÉES:")
paid_unconfirmed = Reservation.objects.filter(
    status='pending'
).filter(
    payment__status='paid'
)
print(f"  Réservations payées non confirmées: {paid_unconfirmed.count()}")
for res in paid_unconfirmed:
    print(f"    Réservation {res.id}: {res.user.email}")

print("\n=== RECOMMANDATIONS ===")
print("1. Si webhook non configuré: Configurer STRIPE_WEBHOOK_SECRET dans settings")
print("2. Si email non envoyé: Configurer EMAIL_HOST, EMAIL_PORT, etc.")
print("3. Créer une notification interne pour les admins")
print("4. Ajouter un badge sur le dashboard admin")
