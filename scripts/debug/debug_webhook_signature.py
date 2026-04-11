# Script pour déboguer la signature webhook
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
import stripe
import hmac
import hashlib

print("=== DÉBOGAGE SIGNATURE WEBHOOK ===")

# Vérifier la configuration
print(f"Stripe Secret Key: {'Configuré' if settings.STRIPE_SECRET_KEY else 'NON CONFIGURÉ'}")
print(f"Stripe Webhook Secret: {getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'NON CONFIGURÉ')}")

# Test de signature
webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
if webhook_secret:
    print(f"\n✅ Webhook Secret trouvé: {webhook_secret[:20]}...")
    
    # Simuler une signature
    payload = '{"type": "checkout.session.completed", "data": {}}'
    timestamp = '1234567890'
    signed_payload = f"{timestamp}.{payload}"
    
    signature = hmac.new(
        webhook_secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"🔑 Signature générée: {signature}")
    print(f"📋 Format attendu: t={timestamp},v1={signature}")
    
else:
    print(f"❌ Webhook Secret NON configuré")

print(f"\n=== VÉRIFICATION VUE WEBHOOK ===")

# Vérifier la vue webhook
try:
    from payments.stripe_views import stripe_webhook
    print(f"✅ Vue stripe_webhook trouvée")
except ImportError:
    print(f"❌ Vue stripe_webhook NON trouvée")

# Vérifier l'URL
try:
    from django.urls import reverse
    webhook_url = reverse('stripe_webhook')
    print(f"✅ URL webhook: {webhook_url}")
except:
    print(f"❌ URL webhook NON trouvée")

print(f"\n=== RECOMMANDATIONS ===")
print(f"1. Vérifiez que STRIPE_WEBHOOK_SECRET est identique dans Stripe et Django")
print(f"2. Redémarrez le serveur Django après modification")
print(f"3. Vérifiez les logs pour voir l'erreur exacte")
