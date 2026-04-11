# Script pour vérifier le ticket_number en double
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket

print("=== VÉRIFICATION TICKET_NUMBER TKT-D5F4D092 ===")

# Chercher le ticket avec ce numéro
ticket_number = "TKT-D5F4D092"
tickets = Ticket.objects.filter(ticket_number=ticket_number)

print(f"Tickets avec le numéro {ticket_number}: {tickets.count()}")

for ticket in tickets:
    print(f"\nTicket {ticket.id}:")
    print(f"  Ticket Number: {ticket.ticket_number}")
    print(f"  Reservation ID: {ticket.reservation.id}")
    print(f"  Reservation User: {ticket.reservation.user.email}")
    print(f"  Generated: {ticket.generated_at}")
    print(f"  Created: {ticket.created_at}")

print(f"\n=== SOLUTION ===")
if tickets.count() > 0:
    print(f"Le ticket {ticket_number} existe déjà pour la réservation {tickets.first().reservation.id}")
    print(f"Options:")
    print(f"1. Supprimer ce ticket et en créer un nouveau pour la réservation 19")
    print(f"2. Utiliser un autre numéro de ticket pour la réservation 19")
    
    # Supprimer le ticket existant
    print(f"\nSuppression du ticket existant...")
    tickets.first().delete()
    print(f"Ticket {ticket_number} supprimé")
    
    # Créer un nouveau ticket pour la réservation 19
    from reservations.models import Reservation
    reservation = Reservation.objects.get(id=19)
    new_ticket = Ticket.objects.create(reservation=reservation)
    print(f"Nouveau ticket créé: {new_ticket.ticket_number}")
else:
    print(f"Aucun ticket trouvé avec le numéro {ticket_number}")
    print(f"L'erreur vient probablement de la génération du numéro")

print(f"\n=== TEST GÉNÉRATION TICKET ===")
# Tester la génération de ticket pour la réservation 19
from reservations.models import Reservation
reservation = Reservation.objects.get(id=19)

try:
    from tickets.models import Ticket
    ticket = Ticket.objects.create(reservation=reservation)
    print(f"Ticket créé avec succès: {ticket.ticket_number}")
except Exception as e:
    print(f"Erreur création ticket: {e}")

print(f"\n=== INSTRUCTIONS ===")
print(f"1. Allez sur: http://127.0.0.1:8000/reservations/19/")
print(f"2. Cliquez sur 'Générer le Ticket'")
print(f"3. Le ticket devrait maintenant être créé correctement")
print(f"4. Cliquez sur 'Télécharger le Ticket' pour le télécharger")
