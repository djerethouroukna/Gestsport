import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from users.models import User

print("=== VÉRIFICATION RÉSERVATION 12 ===")

try:
    reservation = Reservation.objects.get(id=12)
    print(f"Réservation 12 trouvée:")
    print(f"  User: {reservation.user.email if reservation.user else 'None'}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    print(f"  Is payment pending validation: {reservation.is_payment_pending_validation}")
    print(f"  Has ticket: {hasattr(reservation, 'ticket') and reservation.ticket is not None}")
    print(f"  Terrain: {reservation.terrain.name if reservation.terrain else 'None'}")
    
    # Vérifier les conditions pour le bouton de paiement
    print(f"\n=== CONDITIONS BOUTON PAIEMENT ===")
    conditions = {
        'reservation.user == request.user': 'Nécessite connexion',
        'reservation.status == "confirmed"': reservation.status == 'confirmed',
        'not reservation.is_paid': not reservation.is_paid,
        'not reservation.is_payment_pending_validation': not reservation.is_payment_pending_validation
    }
    
    for condition, result in conditions.items():
        print(f"  {condition}: {result}")
    
    # Si la réservation n'est pas confirmée, vérifier le statut
    if reservation.status != 'confirmed':
        print(f"\n❌ PROBLÈME: Réservation non confirmée ({reservation.status})")
        print(f"   Le bouton de paiement n'apparaît que pour les réservations confirmées")
        
    # Si déjà payée
    if reservation.is_paid:
        print(f"\n❌ PROBLÈME: Réservation déjà payée")
        print(f"   Le bouton de paiement n'apparaît que pour les réservations non payées")
        
    # Si paiement en attente de validation
    if reservation.is_payment_pending_validation:
        print(f"\n❌ PROBLÈME: Paiement en attente de validation")
        print(f"   Le bouton de paiement n'apparaît pas quand le paiement est en validation")
        
except Reservation.DoesNotExist:
    print("❌ Réservation 12 n'existe pas")
except Exception as e:
    print(f"❌ Erreur: {e}")

print(f"\n=== UTILISATEURS COACH DISPONIBLES ===")
coaches = User.objects.filter(role='coach')
for coach in coaches:
    print(f"  Coach: {coach.email}")

# Si la réservation existe mais n'appartient à personne
try:
    reservation = Reservation.objects.get(id=12)
    if not reservation.user or reservation.user.email == 'None':
        print(f"\n❌ PROBLÈME: La réservation 12 n'a pas de propriétaire valide")
        print(f"   User: {reservation.user}")
        print(f"   SOLUTION: Créer une réservation pour un coach valide")
        
        # Créer une réservation de test pour le coach
        from terrains.models import Terrain
        from datetime import datetime, timedelta
        from decimal import Decimal
        
        coach = User.objects.filter(role='coach').first()
        terrain = Terrain.objects.first()
        
        if coach and terrain:
            new_reservation = Reservation.objects.create(
                user=coach,
                terrain=terrain,
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=2),
                status='confirmed',
                total_amount=Decimal('10000.00')
            )
            print(f"✅ Nouvelle réservation créée: {new_reservation.id}")
            print(f"   URL: http://127.0.0.1:8000/reservations/{new_reservation.id}/")
            print(f"   Connectez-vous avec: {coach.email}")
            
except Exception as e:
    print(f"Erreur création réservation: {e}")
