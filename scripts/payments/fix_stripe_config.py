import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import stripe
from django.conf import settings

print("=== CORRECTION CONFIGURATION STRIPE ===")

# Forcer la configuration de la clé API
stripe.api_key = settings.STRIPE_SECRET_KEY

print(f"Clé API configurée: {stripe.api_key[:20]}...")

# Tester la connexion
try:
    # Test simple
    account = stripe.Account.retrieve()
    print(f"✅ Connexion Stripe réussie")
    print(f"   Account ID: {account.id}")
    print(f"   Country: {account.country}")
    
    # Tester la balance
    balance = stripe.Balance.retrieve()
    print(f"   Balance: {balance.available}")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    
    # Vérifier si la clé est valide
    if "test" in settings.STRIPE_SECRET_KEY:
        print("✅ Clé de test détectée")
    else:
        print("❌ Clé de test non détectée")
    
    if "sk_test_" in settings.STRIPE_SECRET_KEY:
        print("✅ Format sk_test_ correct")
    else:
        print("❌ Format sk_test_ incorrect")

# Vérifier les URLs de réservations
try:
    from django.urls import reverse
    success_url = reverse('reservations:payment_success', kwargs={'pk': 13})
    cancel_url = reverse('reservations:payment_cancel', kwargs={'pk': 13})
    print(f"\n✅ URLs de paiement:")
    print(f"   Success: {success_url}")
    print(f"   Cancel: {cancel_url}")
except Exception as e:
    print(f"❌ Erreur URLs: {e}")

print(f"\n=== INSTRUCTIONS POUR TESTER ===")
print(f"1. Utilisez la carte: 4242 4242 4242 4242")
print(f"2. Date expiration: 12/34 (ou n'importe quelle date future)")
print(f"3. CVC: 123")
print(f"4. Code postal: 12345")
print(f"5. Nom sur la carte: Laissez vide ou mettez 'Test User'")
print(f"6. Pays: Sélectionnez 'United States'")

print(f"\n=== SI ÇA NE FONCTIONNE TOUJOURS PAS ===")
print(f"1. Vérifiez que vous êtes bien en mode test (pas mode live)")
print(f"2. Assurez-vous d'utiliser un navigateur normal (pas incognito)")
print(f"3. Essayez de vider le cache du navigateur")
print(f"4. Vérifiez que le domaine 127.0.0.1 est autorisé dans Stripe Dashboard")

# Créer une session de test simple
try:
    from payments.stripe_service import StripeService
    from reservations.models import Reservation
    
    class MockRequest:
        def build_absolute_uri(self, url):
            return f"http://127.0.0.1:8000{url}"
    
    reservation = Reservation.objects.get(id=13)
    request = MockRequest()
    
    session_data = StripeService.create_checkout_session(reservation, request)
    
    if isinstance(session_data, dict):
        print(f"\n✅ Session créée (dict): {session_data.get('id', 'No ID')}")
        print(f"   URL: {session_data.get('url', 'No URL')}")
    else:
        print(f"\n✅ Session créée (object): {session_data.id}")
        print(f"   URL: {session_data.url}")
        
except Exception as e:
    print(f"❌ Erreur session: {e}")
    import traceback
    traceback.print_exc()
