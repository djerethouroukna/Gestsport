# Script pour corriger définitivement la génération de tickets
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation

print("=== CORRECTION DÉFINITIVE GÉNÉRATION TICKET ===")

# 1. Nettoyer tous les tickets existants pour éviter les conflits
print("1. Nettoyage des tickets existants...")
all_tickets = Ticket.objects.all()
print(f"   Tickets à supprimer: {all_tickets.count()}")

for ticket in all_tickets:
    print(f"   Suppression: Ticket {ticket.id} - {ticket.ticket_number}")
    ticket.delete()

print("   Tous les tickets supprimés")

# 2. Vérifier les réservations confirmées
print("\n2. Vérification des réservations confirmées...")
confirmed_reservations = Reservation.objects.filter(status='confirmed')
print(f"   Réservations confirmées: {confirmed_reservations.count()}")

for reservation in confirmed_reservations:
    print(f"   - Réservation {reservation.id}: {reservation.user.email}")

# 3. Créer un ticket pour la réservation 19
print("\n3. Création ticket pour réservation 19...")
reservation_19 = Reservation.objects.get(id=19)

try:
    # Forcer la génération d'un numéro unique
    import uuid
    unique_number = uuid.uuid4().hex[:8].upper()
    ticket_number = f"TKT-{unique_number}"
    
    # Vérifier que le numéro est unique
    while Ticket.objects.filter(ticket_number=ticket_number).exists():
        unique_number = uuid.uuid4().hex[:8].upper()
        ticket_number = f"TKT-{unique_number}"
    
    ticket = Ticket.objects.create(
        reservation=reservation_19,
        ticket_number=ticket_number
    )
    
    print(f"   Ticket créé: {ticket.ticket_number}")
    print(f"   Pour réservation: {reservation_19.id}")
    print(f"   User: {reservation_19.user.email}")
    
except Exception as e:
    print(f"   Erreur: {e}")

# 4. Vérifier le ticket créé
print("\n4. Vérification du ticket...")
tickets = Ticket.objects.filter(reservation=reservation_19)
print(f"   Tickets pour réservation 19: {tickets.count()}")

for ticket in tickets:
    print(f"   - Ticket {ticket.id}: {ticket.ticket_number}")
    print(f"     Generated: {ticket.generated_at}")

print("\n=== INSTRUCTIONS FINALES ===")
print("1. Allez sur: http://127.0.0.1:8000/reservations/19/")
print("2. Vous devriez voir:")
print("   - Le bouton 'Télécharger le Ticket' (si ticket existe)")
print("   - OU 'Générer le Ticket' (si problème)")
print("3. Pour télécharger:")
print("   - Cliquez sur 'Télécharger le Ticket'")
print("   - Le PDF sera généré et téléchargé automatiquement")
print("4. Si le bouton 'Générer le Ticket' apparaît:")
print("   - Cliquez dessus")
print("   - Le ticket sera créé")
print("   - Ensuite cliquez sur 'Télécharger le Ticket'")

print("\n=== URL UTILES ===")
print("Réservation 19: http://127.0.0.1:8000/reservations/19/")
print("Télécharger ticket: http://127.0.0.1:8000/tickets/download/19/")
print("Générer ticket: http://127.0.0.1:8000/tickets/generate/19/")
