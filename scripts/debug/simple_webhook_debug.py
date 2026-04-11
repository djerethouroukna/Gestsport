# Script simple pour déboguer le webhook
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings

print("=== DEBUG WEBHOOK SIMPLE ===")

print(f"Stripe Secret Key: {'Configuré' if settings.STRIPE_SECRET_KEY else 'NON CONFIGURÉ'}")
print(f"Stripe Webhook Secret: {getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'NON CONFIGURÉ')}")

# Vérifier la vue webhook
try:
    from payments.stripe_views import stripe_webhook
    print("Vue stripe_webhook trouvée")
except ImportError:
    print("Vue stripe_webhook NON trouvée")

# Vérifier l'URL
try:
    from django.urls import reverse
    webhook_url = reverse('stripe_webhook')
    print(f"URL webhook: {webhook_url}")
except:
    print("URL webhook NON trouvée")

print("\n=== RECOMMANDATIONS ===")
print("1. Vérifiez que STRIPE_WEBHOOK_SECRET est identique dans Stripe et Django")
print("2. Redémarrez le serveur Django après modification")
print("3. Vérifiez les logs pour voir l'erreur exacte")

# Test de la vue webhook directement
print("\n=== TEST VUE WEBHOOK ===")
try:
    from django.test import Client
    client = Client()
    
    # Créer un payload de test
    import json
    test_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "payment_status": "paid",
                "metadata": {
                    "reservation_id": "18"
                }
            }
        }
    }
    
    response = client.post(
        '/payments/stripe/webhook/',
        data=json.dumps(test_payload),
        content_type='application/json',
        HTTP_STRIPE_SIGNATURE='test_signature'
    )
    
    print(f"Status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.content}")
    
except Exception as e:
    print(f"Erreur test: {e}")
