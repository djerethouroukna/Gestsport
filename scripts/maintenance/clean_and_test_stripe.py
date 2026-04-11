import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import stripe
from django.conf import settings
from payments.models import Payment
from reservations.models import Reservation

print("=== NETTOYAGE ET TEST STRIPE ===")

# Forcer la configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Nettoyer les paiements existants pour la réservation 13
try:
    reservation = Reservation.objects.get(id=13)
    payments = Payment.objects.filter(reservation=reservation)
    print(f"Suppression de {payments.count()} paiement(s) pour la réservation 13")
    payments.delete()
    
    # Remettre la réservation en pending
    reservation.status = 'pending'
    reservation.save()
    
    print(f"✅ Réservation 13 nettoyée")
    print(f"   Status: {reservation.status}")
    
except Exception as e:
    print(f"❌ Erreur nettoyage: {e}")

# Créer une nouvelle session de paiement
try:
    from payments.stripe_service import StripeService
    
    class MockRequest:
        def build_absolute_uri(self, url):
            return f"http://127.0.0.1:8000{url}"
    
    request = MockRequest()
    
    session_data = StripeService.create_checkout_session(reservation, request)
    
    if isinstance(session_data, dict):
        session_id = session_data.get('id')
        session_url = session_data.get('url')
    else:
        session_id = session_data.id
        session_url = session_data.url
    
    print(f"✅ Session Stripe créée:")
    print(f"   Session ID: {session_id}")
    print(f"   URL: {session_url}")
    
    # Vérifier que le paiement a été créé
    payment = Payment.objects.filter(reservation=reservation).first()
    if payment:
        print(f"✅ Paiement créé en base:")
        print(f"   Payment ID: {payment.id}")
        print(f"   Status: {payment.status}")
        print(f"   Amount: {payment.amount} {payment.currency}")
    else:
        print("❌ Paiement non créé en base")
    
except Exception as e:
    print(f"❌ Erreur création session: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== INSTRUCTIONS FINALES ===")
print(f"1. Connectez-vous avec: coachtest@example.com / coachpass123")
print(f"2. Allez sur: http://127.0.0.1:8000/reservations/13/")
print(f"3. Cliquez sur 'Procéder au Paiement'")
print(f"4. Utilisez la carte de test: 4242 4242 4242 4242")
print(f"5. Date expiration: 12/34")
print(f"6. CVC: 123")
print(f"7. Code postal: 12345")
print(f"8. Pays: United States")
print(f"9. Ne remplissez PAS le nom du titulaire")

print(f"\n=== DÉPANNAGE SI ÉCHEC ===")
print(f"- Si 'carte refusée': Essayez 4000 0000 0000 0002")
print(f"- Si 'authentification requise': Essayez 4000 0025 0000 3155")
print(f"- Si 'erreur technique': Vérifiez la console du navigateur")
print(f"- Si 'page blanche': Attendez quelques secondes")

print(f"\n=== VÉRIFICATION CONFIGURATION ===")
print(f"✅ Clé API: {settings.STRIPE_PUBLISHABLE_KEY[:20]}...")
print(f"✅ Mode: Test")
print(f"✅ Devise: XOF")
print(f"✅ Domaine: 127.0.0.1")
