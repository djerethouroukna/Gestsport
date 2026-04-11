# Script pour créer un webhook Stripe automatique
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings

print("=== CONFIGURATION WEBHOOK STRIPE AUTOMATIQUE ===")

# Vérifier la configuration actuelle
print(f"Stripe Secret Key: {'Configuré' if settings.STRIPE_SECRET_KEY else 'NON CONFIGURÉ'}")
print(f"Stripe Publishable Key: {'Configuré' if settings.STRIPE_PUBLISHABLE_KEY else 'NON CONFIGURÉ'}")
print(f"Stripe Webhook Secret: {'Configuré' if getattr(settings, 'STRIPE_WEBHOOK_SECRET', None) else 'NON CONFIGURÉ'}")

# Générer un webhook secret si non configuré
if not getattr(settings, 'STRIPE_WEBHOOK_SECRET', None):
    import secrets
    webhook_secret = secrets.token_urlsafe(32)
    print(f"\n🔧 Webhook Secret généré:")
    print(f"  {webhook_secret}")
    print(f"\n📝 Ajoutez ceci dans config/settings.py:")
    print(f"  STRIPE_WEBHOOK_SECRET = '{webhook_secret}'")
    
    print(f"\n🌐 Configurez le webhook dans Stripe Dashboard:")
    print(f"  1. Allez sur https://dashboard.stripe.com/webhooks")
    print(f"  2. Cliquez sur 'Add endpoint'")
    print(f"  3. URL: http://127.0.0.1:8000/payments/stripe/webhook/")
    print(f"  4. Secret: {webhook_secret}")
    print(f"  5. Événements à écouter:")
    print(f"     - checkout.session.completed")
    print(f"     - payment_intent.succeeded")
    print(f"     - payment_intent.payment_failed")
else:
    print(f"\n✅ Webhook déjà configuré")

# Créer un script de test pour le webhook
webhook_test_script = '''
import stripe
from django.conf import settings

# Configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

# Test webhook
try:
    # Créer un événement de test
    event = stripe.Webhook.construct_event(
        payload=b'{"type": "checkout.session.completed", "data": {"object": {"id": "cs_test_123"}}}',
        sig_header='v1=test_signature',
        secret=settings.STRIPE_WEBHOOK_SECRET
    )
    print("✅ Webhook configuré correctement")
except Exception as e:
    print(f"❌ Erreur webhook: {e}")
'''

with open('test_webhook.py', 'w') as f:
    f.write(webhook_test_script)

print(f"\n🧪 Script de test créé: test_webhook.py")

# Vérifier les paiements en attente de synchronisation
from payments.models import Payment
from reservations.models import Reservation

print(f"\n🔍 Vérification des paiements en attente...")

pending_payments = Payment.objects.filter(status='pending')
print(f"Paiements pending: {pending_payments.count()}")

for payment in pending_payments:
    print(f"\nPayment {payment.id}:")
    print(f"  Reservation: {payment.reservation.id}")
    print(f"  Amount: {payment.amount}")
    print(f"  Notes: {payment.notes}")
    
    if 'Session:' in payment.notes:
        session_id = payment.notes.split('Session: ')[1]
        print(f"  Session ID: {session_id}")
        
        try:
            import stripe
            session = stripe.checkout.Session.retrieve(session_id)
            print(f"  Stripe status: {session.status}")
            print(f"  Payment status: {session.payment_status}")
            
            if session.payment_status == 'paid':
                print(f"  ✅ Doit être synchronisé!")
                
        except Exception as e:
            print(f"  ❌ Erreur vérification: {e}")

print(f"\n=== SOLUTIONS ===")
print(f"1. Configurez STRIPE_WEBHOOK_SECRET dans settings.py")
print(f"2. Configurez le webhook dans Stripe Dashboard")
print(f"3. Testez avec: python test_webhook.py")
print(f"4. Redémarrez le serveur Django")

print(f"\n=== SI PROBLÈME PERSISTE ===")
print(f"Le webhook Stripe est essentiel pour la synchronisation automatique.")
print(f"Sans webhook, les paiements resteront en 'pending' même si réussis.")
