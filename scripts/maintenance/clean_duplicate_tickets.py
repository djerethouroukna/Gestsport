# Script pour nettoyer les tickets en double
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation

print("=== NETTOYAGE TICKETS EN DOUBLE ===")

# Vérifier la réservation 19
try:
    reservation = Reservation.objects.get(id=19)
    print(f"Réservation 19:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    
    # Vérifier les tickets pour cette réservation
    tickets = Ticket.objects.filter(reservation=reservation)
    print(f"\nTickets trouvés: {tickets.count()}")
    
    for ticket in tickets:
        print(f"\nTicket {ticket.id}:")
        print(f"  Ticket Number: {ticket.ticket_number}")
        print(f"  Generated: {ticket.generated_at}")
        print(f"  PDF Path: {ticket.pdf_path}")
        print(f"  Created: {ticket.created_at}")
    
    # S'il y a plusieurs tickets, supprimer les anciens
    if tickets.count() > 1:
        print(f"\n🧹 Nettoyage des anciens tickets...")
        for ticket in tickets.order_by('-generated_at')[1:]:  # Garder le plus récent
            print(f"  Suppression ticket {ticket.id} - {ticket.ticket_number}")
            ticket.delete()
    
    # Vérifier après nettoyage
    remaining_tickets = Ticket.objects.filter(reservation=reservation)
    print(f"\nTickets restants: {remaining_tickets.count()}")
    
    if remaining_tickets.count() == 1:
        ticket = remaining_tickets.first()
        print(f"  Ticket conservé: {ticket.ticket_number}")
        print(f"  Generated: {ticket.generated_at}")
    
    # Si aucun ticket, en créer un nouveau
    if remaining_tickets.count() == 0:
        print(f"\n🎫 Création d'un nouveau ticket...")
        from tickets.models import Ticket
        ticket = Ticket.objects.create(reservation=reservation)
        print(f"  Nouveau ticket créé: {ticket.ticket_number}")
    
except Reservation.DoesNotExist:
    print(f"❌ Réservation 19 non trouvée")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== VÉRIFICATION AUTRES RÉSERVATIONS ===")

# Vérifier s'il y a d'autres doublons de ticket_number
ticket_numbers = {}
duplicates = []

for ticket in Ticket.objects.all():
    if ticket.ticket_number in ticket_numbers:
        duplicates.append(ticket.ticket_number)
    else:
        ticket_numbers[ticket.ticket_number] = ticket.id

if duplicates:
    print(f"\n⚠️  Numéros de ticket en double: {duplicates}")
    
    for ticket_number in duplicates:
        tickets_with_same_number = Ticket.objects.filter(ticket_number=ticket_number)
        print(f"\nTicket Number {ticket_number}: {tickets_with_same_number.count()} tickets")
        
        for ticket in tickets_with_same_number:
            print(f"  - Ticket {ticket.id} - Réservation {ticket.reservation.id}")
        
        # Garder le plus récent
        newest = tickets_with_same_number.order_by('-generated_at').first()
        print(f"  Conservation: Ticket {newest.id}")
        
        # Supprimer les autres
        for ticket in tickets_with_same_number.order_by('-generated_at')[1:]:
            print(f"  Suppression: Ticket {ticket.id}")
            ticket.delete()
else:
    print(f"\n✅ Aucun doublon de ticket_number trouvé")

print(f"\n=== NETTOYAGE TERMINÉ ===")
print(f"1. Réessayez de générer le ticket pour la réservation 19")
print(f"2. Le ticket devrait maintenant être créé correctement")
print(f"3. Vous pourrez le télécharger")
