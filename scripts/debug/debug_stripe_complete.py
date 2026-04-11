import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payments.stripe_service import StripeService
from reservations.models import Reservation
from django.conf import settings

# Test complet avec debugging
try:
    reservation = Reservation.objects.get(id=43)  # Réservation avec 5625 FCFA
    print(f'=== DEBUG RÉSERVATION {reservation.id} ===')
    print(f'Terrain: {reservation.terrain.name}')
    print(f'Montant BD: {reservation.total_amount} FCFA')
    print(f'Start_time (BD): {reservation.start_time}')
    print(f'start_time (local): {reservation.start_time.astimezone()}')
    print(f'end_time (BD): {reservation.end_time}')
    print(f'end_time (local): {reservation.end_time.astimezone()}')
    
    # Vérifier le montant dans le service
    print(f'\\n=== VÉRIFICATION SERVICE ===')
    amount_cents = int(reservation.total_amount)
    print(f'amount_cents calculé: {amount_cents}')
    
    # Simuler la création de session
    class MockRequest:
        def build_absolute_uri(self, path):
            return f'http://127.0.0.1:8000{path}'
    
    request = MockRequest()
    
    # Créer la session
    result = StripeService.create_checkout_session(reservation, request)
    
    if result['success']:
        print(f'Session créée: {result["session_url"]}')
        print(f'Montant retourné par service: {result["amount"]} FCFA')
        
        # Vérifier la correspondance
        if result["amount"] == reservation.total_amount:
            print('✅ Service: CORRECT')
        else:
            print(f'❌ Service: ERREUR - Différence: {result["amount"] - reservation.total_amount}')
    else:
        print(f'❌ Erreur service: {result["error"]}')
        
    # Vérifier les settings
    print(f'\\n=== SETTINGS STRIPE ===')
    print(f'Publishable key: {settings.STRIPE_PUBLISHABLE_KEY[:20]}...')
    print(f'Currency setting: {settings.PAYMENT_SETTINGS.get("currency", "NON DÉFINI")}')
        
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
