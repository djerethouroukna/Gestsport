import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation

print("=== NETTOYAGE TICKETS ORPHELINS ===")

# Vérifier tous les tickets
all_tickets = Ticket.objects.all()
print(f"Total tickets: {all_tickets.count()}")

# Vérifier les tickets sans réservation
orphan_tickets = []
for ticket in all_tickets:
    try:
        reservation = ticket.reservation
        print(f"✅ Ticket {ticket.ticket_number} -> Réservation {reservation.id}")
    except Reservation.DoesNotExist:
        orphan_tickets.append(ticket)
        print(f"❌ Ticket {ticket.ticket_number} -> Réservation INEXISTANTE")

if orphan_tickets:
    print(f"\n🗑️  Suppression de {len(orphan_tickets)} tickets orphelins...")
    for ticket in orphan_tickets:
        print(f"  Suppression: {ticket.ticket_number}")
        ticket.delete()
    print(f"✅ Tickets orphelins supprimés")
else:
    print(f"\n✅ Aucun ticket orphelin trouvé")

# Vérifier les doublons de ticket_number
print(f"\n🔍 Vérification des doublons...")
ticket_numbers = {}
for ticket in Ticket.objects.all():
    if ticket.ticket_number in ticket_numbers:
        ticket_numbers[ticket.ticket_number].append(ticket)
    else:
        ticket_numbers[ticket.ticket_number] = [ticket]

duplicates = {num: tickets for num, tickets in ticket_numbers.items() if len(tickets) > 1}
if duplicates:
    print(f"❌ Doublons trouvés:")
    for num, tickets in duplicates.items():
        print(f"  {num}: {len(tickets)} occurrences")
        for ticket in tickets:
            print(f"    - ID: {ticket.id}, Réservation: {ticket.reservation.id if ticket.reservation else 'None'}")
    
    print(f"\n🗑️  Suppression des doublons...")
    for num, tickets in duplicates.items():
        # Garder le premier, supprimer les autres
        for ticket in tickets[1:]:
            print(f"  Suppression: {num} (ID: {ticket.id})")
            ticket.delete()
    print(f"✅ Doublons supprimés")
else:
    print(f"✅ Aucun doublon trouvé")

# Vérifier l'état final
print(f"\n📊 État final:")
final_tickets = Ticket.objects.all()
print(f"  Total tickets: {final_tickets.count()}")

for ticket in final_tickets:
    print(f"    {ticket.ticket_number} -> Réservation {ticket.reservation.id}")

print(f"\n=== TEST CRÉATION TICKET ===")
# Tester la création d'un ticket pour la réservation 13
try:
    reservation = Reservation.objects.get(id=13)
    print(f"Réservation 13: {reservation.status} - {reservation.is_paid}")
    
    # Vérifier si un ticket existe déjà
    existing = Ticket.objects.filter(reservation=reservation).first()
    if existing:
        print(f"✅ Ticket existe déjà: {existing.ticket_number}")
    else:
        print(f"❌ Aucun ticket pour la réservation 13")
        
        # Créer un ticket manuellement
        import uuid
        from django.utils import timezone
        
        # Générer un numéro unique
        max_attempts = 10
        for _ in range(max_attempts):
            ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            if not Ticket.objects.filter(ticket_number=ticket_number).exists():
                break
        
        print(f"🎫 Création ticket: {ticket_number}")
        ticket = Ticket.objects.create(
            reservation=reservation,
            ticket_number=ticket_number
        )
        print(f"✅ Ticket créé: {ticket.ticket_number}")
        
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
