import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from tickets.models import Ticket

print("=== CORRECTION GÉNÉRATION TICKET ===")

# Vérifier la réservation 13
try:
    reservation = Reservation.objects.get(id=13)
    print(f"Réservation 13:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    
    # Vérifier les tickets existants
    tickets = Ticket.objects.filter(reservation=reservation)
    print(f"\nTickets existants: {tickets.count()}")
    
    for ticket in tickets:
        print(f"  Ticket {ticket.ticket_number}:")
        print(f"    Generated: {ticket.generated_at}")
        print(f"    QR Code: {'Oui' if ticket.qr_code else 'Non'}")
        print(f"    Is used: {ticket.is_used}")
    
    # Si un ticket existe, le supprimer pour permettre une nouvelle génération
    if tickets.exists():
        print(f"\n🗑️  Suppression des tickets existants...")
        tickets.delete()
        print(f"✅ Tickets supprimés")
    
    # Créer un nouveau ticket
    print(f"\n🎫 Création d'un nouveau ticket...")
    try:
        ticket = Ticket.objects.create(reservation=reservation)
        print(f"✅ Ticket créé: {ticket.ticket_number}")
        print(f"  Generated: {ticket.generated_at}")
        
        # Vérifier le QR code
        print(f"  QR Code généré: {'Oui' if ticket.qr_code else 'Non'}")
        
    except Exception as e:
        print(f"❌ Erreur création ticket: {e}")
        import traceback
        traceback.print_exc()
    
    # Vérifier l'état final
    print(f"\n📊 État final:")
    final_tickets = Ticket.objects.filter(reservation=reservation)
    print(f"  Tickets: {final_tickets.count()}")
    
    for ticket in final_tickets:
        print(f"    {ticket.ticket_number} - QR: {'Oui' if ticket.qr_code else 'Non'}")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== TEST DES URLS ===")
print(f"1. Connectez-vous en coach: coachtest@example.com")
print(f"2. Allez sur: http://127.0.0.1:8000/reservations/13/")
print(f"3. Cliquez sur 'Générer le Ticket'")
print(f"4. Le PDF devrait se télécharger automatiquement")

print(f"\n=== URLS DIRECTES ===")
print(f"Générer ticket: http://127.0.0.1:8000/tickets/generate/13/")
print(f"Télécharger ticket: http://127.0.0.1:8000/tickets/download/13/")

print(f"\n=== SI PROBLÈME PERSISTE ===")
print(f"Vérifiez le service TicketService.generate_ticket_pdf() dans tickets/services.py")
