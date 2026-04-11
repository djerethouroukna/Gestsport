import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from reservations.models import Reservation
from tickets.models import Ticket

print("=== DIAGNOSTIC GÉNÉRATION TICKET ===")

# Vérifier la réservation 13
try:
    reservation = Reservation.objects.get(id=13)
    print(f"Réservation 13:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    print(f"  Payment status: {reservation.payment_status}")
    
    # Vérifier si un ticket existe déjà
    try:
        ticket = Ticket.objects.get(reservation=reservation)
        print(f"  ✅ Ticket existe: {ticket.ticket_number}")
        print(f"  Created: {ticket.created_at}")
        print(f"  QR Code: {'Généré' if ticket.qr_code else 'Non généré'}")
    except Ticket.DoesNotExist:
        print(f"  ❌ Aucun ticket trouvé")
    
    # Vérifier les permissions
    print(f"\n🔍 Vérifications requises:")
    print(f"  1. Réservation.status == 'confirmed': {reservation.status == 'confirmed'}")
    print(f"  2. Réservation.is_paid == True: {reservation.is_paid}")
    print(f"  3. Ticket.DoesNotExist: {not Ticket.objects.filter(reservation=reservation).exists()}")
    
    # Si la réservation n'est pas confirmée, la confirmer
    if reservation.status != 'confirmed':
        print(f"\n⚠️  La réservation n'est pas confirmée!")
        print(f"   Status actuel: {reservation.status}")
        print(f"   Action requise: L'admin doit confirmer la réservation")
        
        # Vérifier si on peut la confirmer automatiquement pour le test
        if reservation.is_paid:
            print(f"\n🔧 Auto-confirmation pour le test...")
            reservation.status = 'confirmed'
            reservation.confirmation_date = timezone.now()
            reservation.save()
            print(f"✅ Réservation confirmée automatiquement")
            
            # Vérifier à nouveau
            reservation.refresh_from_db()
            print(f"   Nouveau status: {reservation.status}")
        else:
            print(f"❌ Impossible de confirmer: réservation non payée")
    
    # Créer un ticket de test si possible
    if reservation.status == 'confirmed':
        print(f"\n🎫 Test de création de ticket...")
        try:
            ticket = Ticket.objects.create(reservation=reservation)
            print(f"✅ Ticket créé: {ticket.ticket_number}")
        except Exception as e:
            print(f"❌ Erreur création ticket: {e}")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== URLS DE TEST ===")
print(f"Générer ticket: http://127.0.0.1:8000/tickets/generate/13/")
print(f"Télécharger ticket: http://127.0.0.1:8000/tickets/download/13/")
print(f"Détail réservation: http://127.0.0.1:8000/reservations/13/")

print(f"\n=== COMPES ===")
print(f"Coach: coachtest@example.com / coachpass123")
print(f"Admin: admin@example.com / adminpass123")
