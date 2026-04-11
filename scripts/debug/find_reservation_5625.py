import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payments.stripe_service import StripeService
from reservations.models import Reservation

# Chercher une réservation avec le montant 5625
try:
    reservations = Reservation.objects.filter(total_amount=5625.00)
    
    if reservations.exists():
        for reservation in reservations:
            print(f'Trouvé réservation {reservation.id} avec montant 5625 FCFA')
            print(f'Terrain: {reservation.terrain.name}')
            print(f'Status: {reservation.status}')
            
            # Simuler la création de session
            class MockRequest:
                def build_absolute_uri(self, path):
                    return f'http://127.0.0.1:8000{path}'
            
            request = MockRequest()
            
            # Créer la session
            result = StripeService.create_checkout_session(reservation, request)
            
            if result['success']:
                print(f'Montant BD: {reservation.total_amount} FCFA')
                print(f'Montant Stripe: {result["amount"]} FCFA')
                
                # Vérifier la correspondance
                if result["amount"] == reservation.total_amount:
                    print('CORRECT: Pas de multiplication par 100')
                else:
                    print(f'ERREUR: Multiplication par 100 détectée!')
                    print(f'   Attendu: {reservation.total_amount}')
                    print(f'   Reçu: {result["amount"]')
                    print(f'   Ratio: {result["amount"] / reservation.total_amount}x')
            else:
                print(f'Erreur création session: {result["error"]}')
    else:
        print('Aucune réservation trouvée avec montant 5625 FCFA')
        
        # Afficher toutes les réservations avec leurs montants
        all_reservations = Reservation.objects.filter(status='confirmed')[:10]
        print('\\nRéservations existantes:')
        for r in all_reservations:
            print(f'  ID {r.id}: {r.total_amount} FCFA - {r.terrain.name}')
        
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
